"""Write the three required artifacts after successful processing."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from otc_quote_agent.exporters.csv_exporter import CSVExporter
from otc_quote_agent.exporters.html_exporter import HTMLExporter
from otc_quote_agent.exporters.json_exporter import JSONExporter
from otc_quote_agent.schemas import ExtractionResult


class ExportBundle:
    def __init__(self) -> None:
        self.exporters = (JSONExporter(), CSVExporter(), HTMLExporter())

    def render_all(self, result: ExtractionResult) -> dict[str, str]:
        rendered: dict[str, str] = {}
        for exporter in self.exporters:
            filename = (
                exporter.filename_for(result)
                if isinstance(exporter, JSONExporter)
                else exporter.filename
            )
            rendered[filename] = exporter.render(result)
        return rendered

    def export(self, result: ExtractionResult, output_dir: str | Path) -> dict[str, Path]:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        rendered = self.render_all(result)
        temporary: dict[Path, Path] = {}
        try:
            for filename, content in rendered.items():
                target = target_dir / filename
                temp = target_dir / f".{filename}.{uuid4().hex}.tmp"
                temp.write_text(content, encoding="utf-8", newline="")
                temporary[target] = temp
            for target, temp in temporary.items():
                temp.replace(target)
        finally:
            for temp in temporary.values():
                if temp.exists():
                    temp.unlink()
        return {filename: target_dir / filename for filename in rendered}
