from pathlib import Path
import subprocess

import pytest


example_files = list((Path(__file__).parent.parent / "examples").iterdir())


@pytest.mark.parametrize("path", example_files)
def test_example_functional(path: Path) -> None:
    subprocess.check_call(["python3", str(path)])
