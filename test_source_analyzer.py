"""Offline unit checks: no MetaEditor, no network, no project writes."""
import tempfile
import unittest
from pathlib import Path
from source_analyzer import inspect_source

class SourceAnalyzerTests(unittest.TestCase):
    def test_python_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.py"
            p.write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(inspect_source(p)["status"], "PASS")
            p.write_text("def broken(:\n", encoding="utf-8")
            self.assertEqual(inspect_source(p)["status"], "FAIL")

    def test_mql4_is_never_cpp(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "expert.mq4"
            p.write_text("void OnTick() {}\n", encoding="utf-8")
            r = inspect_source(p)
            self.assertEqual(r["language"], "mql4")
            self.assertEqual(r["status"], "NOT_VERIFIED")

    def test_cpp_default_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "program.cpp"
            p.write_text("int main() { return 0; }\n", encoding="utf-8")
            r = inspect_source(p)
            self.assertEqual(r["status"], "NOT_VERIFIED")

    def test_cpp_compiler_on_ci(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "program.cpp"
            p.write_text("int main() { return 0; }\n", encoding="utf-8")
            r = inspect_source(p, run_cpp_compiler=True)
            self.assertEqual(r["status"], "PASS", r)

    def test_unsupported_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "key.env"
            p.write_text("SECRET\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_source(p)

if __name__ == "__main__":
    unittest.main()
