"""Presentation preserves saved teaching values and avoids execution."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

import nbformat


RENDERER = Path(__file__).resolve().parents[1] / "examples" / "render_notebook.py"


class SavedRenderingTest(unittest.TestCase):
    def render(self, *, presentation="primary", visible=(0,), evidence="real"):
        identity = "cnstock.000001.SZ.19910403"
        cell = nbformat.v4.new_code_cell("raise RuntimeError('must not execute')")
        cell.execution_count = 7
        cell.outputs = [
            nbformat.v4.new_output("display_data", data={"text/html":
                f'<table data-ref="{identity}"><tr><td>{identity}</td><td>11.56</td></tr></table>'}),
            nbformat.v4.new_output("stream", name="stdout", text="source digest: abc123\n"),
        ]
        cell.metadata.update(presentation=presentation, visible_outputs=list(visible),
                             example_title="六日价格", example_evidence=evidence)
        notebook = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_markdown_cell("## 1. 第一次取表"), cell])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "researcher_tutorial.ipynb"
            nbformat.write(notebook, path)
            before = json.loads(path.read_text())
            original_bytes = path.read_bytes()
            original_mtime = path.stat().st_mtime_ns
            result = subprocess.run([sys.executable, str(RENDERER), "--notebook", str(path)],
                                    capture_output=True, text=True)
            if result.returncode:
                return result, None, before, json.loads(path.read_text())
            self.assertEqual(path.read_bytes(), original_bytes)
            self.assertEqual(path.stat().st_mtime_ns, original_mtime)
            return result, path.with_suffix(".html").read_text(), before, json.loads(path.read_text())

    def test_primary_query_precedes_table_without_execution(self):
        result, html, before, after = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, after)
        self.assertLess(html.index("must not execute"), html.index("<table data-ref="))
        self.assertIn('<span class="security-code" title="cnstock.000001.SZ.19910403">000001.SZ</span>', html)
        self.assertIn('data-ref="cnstock.000001.SZ.19910403"', html)
        self.assertIn("11.56", html)

    def test_supporting_output_is_retained_in_fold(self):
        result, html, _, _ = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(html.count('data-output-index="'), 2)
        folded = html.index('<details class="supporting-output">')
        self.assertGreater(html.index("source digest: abc123"), folded)

    def test_synthetic_result_is_labelled(self):
        result, html, _, _ = self.render(presentation="result", evidence="synthetic")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("合成示例输出", html)

    def test_invalid_output_index_refuses_render(self):
        result, html, _, _ = self.render(visible=(2,))
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(html)
        self.assertIn("invalid visible_outputs", result.stderr)


if __name__ == "__main__":
    unittest.main()
