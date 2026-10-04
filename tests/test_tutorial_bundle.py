from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest


path = Path(__file__).resolve().parents[1] / "examples/build_library_tutorials.py"
spec = importlib.util.spec_from_file_location("tutorial_bundle", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TutorialBundleTest(unittest.TestCase):
    def test_role_and_chapter_links_work_inside_single_file(self):
        saved = '<html><head><style>body{}</style></head><body><section id="section-2"><a href="#section-2">章节</a><a href="developer_tutorial.html#section-7">另一个角色</a><pre>11.56 &lt; 12</pre></section></body></html>'
        bundled = module.role_body(saved, "researcher", "abc123")
        self.assertIn('id="researcher-section-2"', bundled)
        self.assertIn('href="#researcher-section-2"', bundled)
        self.assertIn('href="#developer-section-7" data-role-target="developer"', bundled)
        self.assertIn('11.56 &lt; 12', bundled)

    def test_relative_document_link_has_fixed_source(self):
        saved = '<html><body><a href="../docs/current-delivery.md">交付</a><pre>x</pre></body></html>'
        bundled = module.role_body(saved, "researcher", "abc123")
        self.assertIn('https://github.com/sinnergarden/axiom-docs/blob/abc123/docs/current-delivery.md', bundled)
        self.assertNotIn('href="../', bundled)

    def test_source_commit_rejects_changed_local_html(self):
        saved = '<html><head><style>body{}</style></head><body><pre>11.56</pre></body></html>'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "notebooks").mkdir()
            for role in ("researcher", "developer"):
                (root / f"notebooks/{role}_tutorial.html").write_text(saved)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "notebooks"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Tutorial Test", "-c", "user.email=test@example.invalid",
                            "commit", "-qm", "fixture"], cwd=root, check=True)
            output = root / "axiom-tutorials.html"
            result = module.build(root, "HEAD", output)
            self.assertEqual(len(result["docs_commit"]), 40)
            (root / "notebooks/researcher_tutorial.html").write_text(saved.replace("11.56", "12.00"))
            before = output.read_bytes()
            with self.assertRaisesRegex(ValueError, "does not match the declared commit"):
                module.build(root, "HEAD", output)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
