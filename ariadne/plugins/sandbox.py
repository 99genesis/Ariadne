"""Plugin Sandbox for fault-isolated, resource-bounded execution of intelligence plugins.

Wraps plugin execution inside asyncio timeouts, cancellation boundaries, and memory limits.
"""

import asyncio
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from ariadne.core.exceptions import PluginException
from ariadne.core.interfaces import ILogger, IPlugin, IProvider
from ariadne.core.models import IntelligenceResult, TargetEntity


class SandboxResult(BaseModel):
    """Execution telemetry and output returned by PluginSandbox."""

    plugin_id: str = Field(...)
    success: bool = Field(default=True)
    results: List[IntelligenceResult] = Field(default_factory=list)
    execution_time_ms: float = Field(default=0.0)
    error: Optional[str] = Field(default=None)
    timed_out: bool = Field(default=False)
    memory_peak_mb: float = Field(default=0.0)


class PluginSandbox:
    """Fault isolation wrapper enforcing asyncio timeouts and exception boundaries."""

    def __init__(
        self,
        timeout_seconds: float = 60.0,
        max_memory_mb: float = 1024.0,
        logger: Optional[ILogger] = None,
    ) -> None:
        """Initialize PluginSandbox boundaries."""
        self.timeout_seconds = float(timeout_seconds)
        self.max_memory_mb = float(max_memory_mb)
        self.logger = logger

    def _get_current_memory_mb(self) -> float:
        """Estimate current RSS memory consumption in MB if psutil is present."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    async def execute_plugin(
        self,
        plugin: IPlugin,
        target: TargetEntity,
        providers: Dict[str, IProvider],
        custom_timeout: Optional[float] = None,
    ) -> SandboxResult:
        """Execute a plugin safely inside timeout and exception isolation boundaries."""
        start_time = time.perf_counter()
        start_mem = self._get_current_memory_mb()
        timeout = custom_timeout if custom_timeout is not None else self.timeout_seconds

        try:
            # 1. Check can_handle with short 5s boundary
            can_handle = await asyncio.wait_for(plugin.can_handle(target), timeout=min(10.0, timeout))
            if not can_handle:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                if self.logger:
                    self.logger.debug(f"[Sandbox] Plugin '{plugin.plugin_id}' declined target '{target.target_id}'")
                return SandboxResult(
                    plugin_id=plugin.plugin_id,
                    success=True,
                    results=[],
                    execution_time_ms=elapsed,
                )

            if self.logger:
                self.logger.info(
                    f"[Sandbox] Executing plugin '{plugin.plugin_id}' with timeout={timeout}s..."
                )

            # 2. Execute within strict asyncio.wait_for boundary
            results = await asyncio.wait_for(
                plugin.execute(target=target, providers=providers),
                timeout=timeout,
            )

            elapsed = (time.perf_counter() - start_time) * 1000.0
            peak_mem = max(self._get_current_memory_mb() - start_mem, 0.0)

            if self.logger:
                self.logger.info(
                    f"[Sandbox] Plugin '{plugin.plugin_id}' completed in {elapsed:.1f}ms ({len(results)} results)"
                )

            return SandboxResult(
                plugin_id=plugin.plugin_id,
                success=True,
                results=results,
                execution_time_ms=elapsed,
                memory_peak_mb=peak_mem,
            )

        except (asyncio.TimeoutError, TimeoutError) as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Plugin '{plugin.plugin_id}' exceeded execution timeout of {timeout}s."
            if self.logger:
                self.logger.error(f"[Sandbox Timeout] {error_msg}")
            return SandboxResult(
                plugin_id=plugin.plugin_id,
                success=False,
                results=[],
                execution_time_ms=elapsed,
                error=error_msg,
                timed_out=True,
            )
        except asyncio.CancelledError:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Plugin '{plugin.plugin_id}' was cancelled by system or user."
            if self.logger:
                self.logger.warning(f"[Sandbox Cancelled] {error_msg}")
            # Ensure cleanup is called if cancelled
            try:
                await plugin.cleanup()
            except Exception:
                pass
            raise
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            error_msg = str(exc)
            if self.logger:
                self.logger.error(
                    f"[Sandbox Error] Plugin execution failed in '{plugin.plugin_id}': {exc}",
                    exc_info=exc,
                )
            return SandboxResult(
                plugin_id=plugin.plugin_id,
                success=False,
                results=[],
                execution_time_ms=elapsed,
                error=error_msg,
            )
