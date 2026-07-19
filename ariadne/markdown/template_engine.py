"""Template Engine using Jinja2 for dynamic markdown generation."""

from pathlib import Path
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateEngine:
    """Renders dynamic markdown notes using Jinja2 templates."""

    DEFAULT_TEMPLATE = (
        "# {{ title }}\n\n"
        "Status\n"
        "Found\n\n"
        "Confidence\n"
        "{{ (confidence_score * 100) | round | int }}%\n\n"
        "{% if technical_details %}"
        "{% for key, value in technical_details.items() %}"
        "{{ key.replace('_', ' ').title() }}\n"
        "{{ value }}\n\n"
        "{% endfor %}"
        "{% endif %}"
        "{% if content_markdown %}"
        "{{ content_markdown }}\n\n"
        "{% endif %}"
        "Relations\n"
        "{% for link in links_to %}"
        "{{ link }}\n"
        "{% endfor %}\n"
        "Tags\n"
        "{% for tag in tags %}"
        "{{ tag }}\n"
        "{% endfor %}"
    )

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        self.templates_dir = templates_dir or Path("Ariadne_Workspace") / "Templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        default_file = self.templates_dir / "note_template.md"
        if not default_file.exists():
            try:
                default_file.write_text(self.DEFAULT_TEMPLATE, encoding="utf-8")
            except Exception:
                pass
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render markdown body using template file or default string template."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception:
            # Fallback to default in-memory template
            from jinja2 import Template
            t = Template(self.DEFAULT_TEMPLATE)
            return t.render(**context)
