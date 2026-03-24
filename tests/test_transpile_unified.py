"""Tests for the unified transpile() entry point and auto-mode detection."""
import textwrap
import pytest
from pathlib import Path
from outputllsp3.transpiler import _detect_transpile_mode


class TestDetectTranspileMode:
    def test_directory_is_build_script(self, tmp_path):
        assert _detect_transpile_mode(tmp_path) == "build_script"

    def test_python_first_robot_proc(self, tmp_path):
        f = tmp_path / "prog.py"
        f.write_text("@robot.proc\ndef my_proc(): pass\n")
        assert _detect_transpile_mode(f) == "python_first"

    def test_python_first_run_main(self, tmp_path):
        f = tmp_path / "prog.py"
        f.write_text("@run.main\ndef main(): pass\n")
        assert _detect_transpile_mode(f) == "python_first"

    def test_build_script_detection(self, tmp_path):
        f = tmp_path / "build.py"
        f.write_text("def build(project, api=None, ns=None): pass\n")
        assert _detect_transpile_mode(f) == "build_script"

    def test_ast_fallback(self, tmp_path):
        f = tmp_path / "prog.py"
        f.write_text("x = 1 + 2\n")
        assert _detect_transpile_mode(f) == "ast"

    def test_python_first_takes_priority_over_build(self, tmp_path):
        f = tmp_path / "prog.py"
        f.write_text("@robot.proc\ndef build(project): pass\n")
        assert _detect_transpile_mode(f) == "python_first"


class TestTranspileSignature:
    def test_transpile_importable(self):
        from outputllsp3 import transpile
        import inspect
        sig = inspect.signature(transpile)
        assert "mode" in sig.parameters
        assert "out" in sig.parameters
        assert sig.parameters["mode"].default == "auto"

    def test_transpile_in_all(self):
        import outputllsp3
        assert "transpile" in outputllsp3.__all__
