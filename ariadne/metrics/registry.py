"""MetricsRegistry implementing IMetricsRegistry for Prometheus and Grafana exporting.

Tracks counters, gauges, and histograms with label dimensionality.
"""

import threading
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from ariadne.core.interfaces import ILogger, IMetricsRegistry


class MetricsRegistry(IMetricsRegistry):
    """Prometheus-compatible in-memory telemetry registry."""

    def __init__(self, logger: Optional[ILogger] = None) -> None:
        """Initialize telemetry structures with thread-safe locking."""
        self.logger = logger
        self._lock = threading.Lock()
        # Key: (metric_name, tuple(sorted(labels.items()))) -> float
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = defaultdict(float)
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = defaultdict(float)
        # Key: (metric_name, tuple(sorted(labels.items()))) -> list of float observations
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List[float]] = defaultdict(list)

    @staticmethod
    def _normalize_labels(labels: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
        """Convert dictionary of labels to sorted tuple representation."""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    @staticmethod
    def _format_labels(labels: Tuple[Tuple[str, str], ...]) -> str:
        """Format label tuple into Prometheus exposition string e.g. {provider="google",status="ok"}."""
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in labels]
        return "{" + ",".join(pairs) + "}"

    def increment_counter(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a monotonic counter by 1."""
        norm = self._normalize_labels(labels)
        with self._lock:
            self._counters[(metric_name, norm)] += 1.0

    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge to an instantaneous value."""
        norm = self._normalize_labels(labels)
        with self._lock:
            self._gauges[(metric_name, norm)] = float(value)

    def record_histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a numeric observation inside a histogram."""
        norm = self._normalize_labels(labels)
        with self._lock:
            self._histograms[(metric_name, norm)].append(float(value))

    def export_prometheus_text(self) -> str:
        """Export all recorded metrics in standard Prometheus exposition format."""
        lines: List[str] = []
        with self._lock:
            # Counters
            names_counters = sorted({key[0] for key in self._counters.keys()})
            for name in names_counters:
                lines.append(f"# TYPE {name} counter")
                for (m_name, labels), val in self._counters.items():
                    if m_name == name:
                        lines.append(f"{name}{self._format_labels(labels)} {val}")

            # Gauges
            names_gauges = sorted({key[0] for key in self._gauges.keys()})
            for name in names_gauges:
                lines.append(f"# TYPE {name} gauge")
                for (m_name, labels), val in self._gauges.items():
                    if m_name == name:
                        lines.append(f"{name}{self._format_labels(labels)} {val}")

            # Histograms (Summary/Count/Sum/Buckets)
            names_histograms = sorted({key[0] for key in self._histograms.keys()})
            for name in names_histograms:
                lines.append(f"# TYPE {name} summary")
                for (m_name, labels), obs in self._histograms.items():
                    if m_name == name and obs:
                        count = len(obs)
                        total = sum(obs)
                        lbl_str = self._format_labels(labels)
                        lines.append(f"{name}_count{lbl_str} {count}")
                        lines.append(f"{name}_sum{lbl_str} {total}")

        return "\n".join(lines) + ("\n" if lines else "")
