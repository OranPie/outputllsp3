"""Unified transpile() entry-point demo.

This file shows how to call the new ``transpile()`` function instead of the
six separate transpile_* functions.  It also demonstrates auto-mode detection
and explicit mode selection.

Run this script directly (it's not itself a build script)::

    python3 examples/07_transpile_unified.py

It writes three .llsp3 files to /tmp using three different input styles.
"""
from pathlib import Path
import tempfile, textwrap

# All three modes through one entry point
from outputllsp3 import transpile


def demo_auto_detect():
    """transpile() with mode='auto' picks the right engine automatically."""
    tmp = Path(tempfile.mkdtemp())

    # Build-script source (has def build(...))
    build_src = tmp / "build_demo.py"
    build_src.write_text(textwrap.dedent("""\
        from outputllsp3 import MotorPair
        def build(project, api, ns=None):
            api.flow.start(
                api.move.set_pair(MotorPair.AB),
                api.wait.seconds(0.5),
                api.move.stop(),
            )
    """))

    # Python-first source (has @run.main)
    pf_src = tmp / "pf_demo.py"
    pf_src.write_text(textwrap.dedent("""\
        from outputllsp3 import robot, run, port
        LEFT = port.A
        RIGHT = port.B

        @run.main
        def main():
            robot.use_pair(RIGHT, LEFT)
            robot.forward_cm(20, 420)
            robot.turn_deg(90, 260)
    """))

    from outputllsp3.workflow import discover_defaults
    defaults = discover_defaults(Path("."))
    if not defaults.get("template") or not defaults.get("strings"):
        print("No ok.llsp3 / strings.json found in working tree — skipping file output.")
        print("But transpile() is importable and mode detection works:")
        from outputllsp3.transpiler import _detect_transpile_mode
        print(f"  build_demo.py → {_detect_transpile_mode(build_src)}")  # build_script
        print(f"  pf_demo.py    → {_detect_transpile_mode(pf_src)}")     # python_first
        return

    out_build = tmp / "out_build.llsp3"
    out_pf    = tmp / "out_pf.llsp3"

    transpile(build_src, out=out_build)  # auto → build_script
    transpile(pf_src,    out=out_pf)     # auto → python_first

    print(f"build_script output : {out_build} ({out_build.stat().st_size} bytes)")
    print(f"python_first output : {out_pf}    ({out_pf.stat().st_size} bytes)")


def demo_explicit_mode():
    """Explicit mode='build_script' bypasses detection."""
    from outputllsp3.transpiler import _detect_transpile_mode
    from pathlib import Path
    import tempfile, textwrap

    tmp = Path(tempfile.mkdtemp())
    # A file that looks like AST source but we force build_script
    src = tmp / "hybrid.py"
    src.write_text(textwrap.dedent("""\
        def build(project, api, ns=None):
            api.flow.start(api.wait.seconds(1))
    """))
    detected = _detect_transpile_mode(src)
    print(f"Auto-detected mode for hybrid.py: {detected}")
    # With mode='build_script' we'd call:
    #   transpile(src, mode='build_script', out='hybrid.llsp3')
    print("Explicit mode='build_script' would compile with build() entry point.")


if __name__ == "__main__":
    demo_auto_detect()
    demo_explicit_mode()
