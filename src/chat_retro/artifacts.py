"""Artifact generation for chat-retro outputs."""


import json
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

from chat_retro.interactive import (
    get_interactive_css,
    get_interactive_init_js,
    get_interactive_js,
)


class ArtifactGenerator:
    """Generate offline-capable HTML and markdown artifacts."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("outputs")

    def _load_d3_js(self) -> str:
        """Load bundled D3.js minified source."""
        try:
            assets = resources.files("chat_retro") / "assets"
            d3_file = assets / "d3.v7.min.js"
            return d3_file.read_text()
        except (FileNotFoundError, TypeError):
            # Fallback for development
            asset_path = Path(__file__).parent / "assets" / "d3.v7.min.js"
            if asset_path.exists():
                return asset_path.read_text()
            return "// D3.js not bundled - visualization disabled"

    def generate_html(
        self,
        title: str,
        data: dict[str, Any],
        visualization_code: str = "",
        include_d3: bool = True,
        interactive: bool = False,
        include_filters: bool = True,
        include_search: bool = True,
        include_details: bool = True,
        include_annotations: bool = True,
    ) -> str:
        """Generate self-contained HTML with inlined dependencies.

        Args:
            title: Page title
            data: Analysis data to embed as JSON
            visualization_code: JavaScript code for visualization
            include_d3: Whether to include D3.js library
            interactive: Whether to include interactive components
            include_filters: Include filter panel (if interactive)
            include_search: Include search (if interactive)
            include_details: Include detail modal (if interactive)
            include_annotations: Include annotations (if interactive)

        Returns:
            Complete HTML string
        """
        d3_script = self._load_d3_js() if include_d3 else ""
        data_json = json.dumps(data, indent=2, default=str)
        timestamp = datetime.now().isoformat()

        # Interactive components
        interactive_css = ""
        interactive_js = ""
        interactive_init = ""
        controls_html = ""

        if interactive:
            interactive_css = get_interactive_css()
            interactive_js = get_interactive_js(
                include_filters=include_filters,
                include_search=include_search,
                include_details=include_details,
                include_annotations=include_annotations,
            )
            interactive_init = get_interactive_init_js(
                include_details=include_details,
                include_annotations=include_annotations,
            )
            controls_html = '<div id="controls"></div>'

        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem;
      background: #fafafa;
    }}
    h1 {{ margin-bottom: 1rem; color: #1a1a1a; }}
    .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 2rem; }}
    #visualization {{
      background: white;
      border-radius: 8px;
      padding: 1rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      min-height: 400px;
    }}
    .error {{ color: #c00; padding: 1rem; }}
    {interactive_css}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">Generated: {timestamp}</div>
  {controls_html}
  <div id="visualization"></div>

  <script>
    // D3.js library (inlined for offline use)
    {d3_script}
  </script>
  <script>
    // Interactive components
    {interactive_js}
    {interactive_init}
  </script>
  <script>
    // Analysis data
    const DATA = {data_json};
  </script>
  <script>
    // Visualization code
    try {{
      {visualization_code if visualization_code else "document.getElementById('visualization').innerHTML = '<p>No visualization configured.</p>';"}
    }} catch (error) {{
      document.getElementById('visualization').innerHTML = '<div class="error">Visualization error: ' + error.message + '</div>';
    }}
  </script>
</body>
</html>
"""

    def generate_markdown(
        self,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Generate markdown reflection/learning output.

        Args:
            title: Document title
            content: Markdown content body
            metadata: Optional frontmatter metadata

        Returns:
            Complete markdown string
        """
        frontmatter = ""
        if metadata:
            frontmatter_lines = ["---"]
            for key, value in metadata.items():
                if isinstance(value, (list, dict)):
                    frontmatter_lines.append(f"{key}: {json.dumps(value)}")
                else:
                    frontmatter_lines.append(f"{key}: {value}")
            frontmatter_lines.append("---\n")
            frontmatter = "\n".join(frontmatter_lines)

        return f"""{frontmatter}# {title}

{content}

---
*Generated by chat-retro on {datetime.now().strftime("%Y-%m-%d")}*
"""

    def save_html(
        self,
        filename: str,
        title: str,
        data: dict[str, Any],
        visualization_code: str = "",
    ) -> Path:
        """Generate and save HTML artifact.

        Args:
            filename: Output filename (without extension)
            title: Page title
            data: Analysis data
            visualization_code: JavaScript visualization code

        Returns:
            Path to saved file
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        html = self.generate_html(title, data, visualization_code)
        output_path = self.output_dir / f"{filename}.html"
        output_path.write_text(html)
        return output_path

    def save_markdown(
        self,
        filename: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Generate and save markdown artifact.

        Args:
            filename: Output filename (without extension)
            title: Document title
            content: Markdown content
            metadata: Optional frontmatter

        Returns:
            Path to saved file
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        md = self.generate_markdown(title, content, metadata)
        output_path = self.output_dir / f"{filename}.md"
        output_path.write_text(md)
        return output_path
