from pathlib import Path
import subprocess

import pytest


example_files = [path for path in (Path(__file__).parent.parent / "examples").iterdir() if path.is_file()]


@pytest.mark.parametrize("path", example_files)
def test_example_functional(path: Path) -> None:
    try:
        subprocess.run(["poetry", "run", "python3", str(path)], check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        if b"usage:" not in e.stderr:
            # process didn't exit from a parser error, reraise
            raise
