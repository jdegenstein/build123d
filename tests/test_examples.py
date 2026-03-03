"""
build123d Example tests

name: test_examples.py
by:   fischman
date: February 21 2025

desc: Unit tests for the build123d examples, ensuring they don't raise.
"""

import os
import sys
import subprocess
from pathlib import Path
import pytest

_root_dir = Path(__file__).resolve().parent.parent
_examples_dir = _root_dir / "examples"
_ttt_dir = _root_dir / "docs" / "assets" / "ttt"

# Collect all example files natively
example_files = [
    f
    for f in list(_examples_dir.iterdir()) + list(_ttt_dir.iterdir())
    if not f.name.startswith("_") and f.name.endswith(".py")
]

_MOCK_OCP_VSCODE_CONTENTS = """
import sys
from unittest.mock import Mock
mock_module = Mock()
mock_module.show = Mock()
mock_module.show_object = Mock()
mock_module.show_all = Mock()
sys.modules["ocp_vscode"] = mock_module
"""


@pytest.mark.parametrize("path", example_files, ids=lambda x: x.name)
def test_example(path, tmp_path):
    """Test that the example executes without raising exceptions."""
    cwd = tmp_path if "benchy" not in path.name else _examples_dir

    # Write the mock module to the temporary directory
    mock_file = tmp_path / "ocp_vscode.py"
    mock_file.write_text(_MOCK_OCP_VSCODE_CONTENTS, encoding="utf-8")

    # Add tmp_path to PYTHONPATH so the mock is naturally imported by the example
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{tmp_path}{os.pathsep}{env.get('PYTHONPATH', '')}"

    # 3. Subprocess run with text=True for clean traceback rendering
    got = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        check=False,
    )

    if got.returncode != 0:
        pytest.fail(
            f"Example {path.name} failed with exit code {got.returncode}.\n\n"
            f"--- STDERR ---\n{got.stderr}\n"
            f"--- STDOUT ---\n{got.stdout}\n"
        )
