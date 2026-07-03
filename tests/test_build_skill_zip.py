import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


def load_build_script():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_skill_zip.py"
    spec = importlib.util.spec_from_file_location("build_skill_zip", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildSkillZipTest(unittest.TestCase):
    def test_build_zip_uses_skill_name_as_top_level_directory(self):
        build = load_build_script()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir()
            (root / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("hello\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_package.py").write_text("pass\n", encoding="utf-8")
            (root / "tools").mkdir()
            (root / "tools" / "debug_probe.py").write_text("print('debug')\n", encoding="utf-8")

            output = Path(td) / "out.zip"
            count = build.build_zip(root, output, build.DEFAULT_EXCLUDES)

            self.assertEqual(count, 2)
            with zipfile.ZipFile(output) as zf:
                self.assertEqual(
                    sorted(zf.namelist()),
                    ["example-skill/README.md", "example-skill/SKILL.md"],
                )


if __name__ == "__main__":
    unittest.main()
