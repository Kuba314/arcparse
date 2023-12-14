from collections.abc import Iterable
from pathlib import Path
import re
import subprocess

import pytest


def python_codeblocks(text: str) -> list[str]:
    return re.findall(r"```py\s*(.*?)\s*```", text, flags=re.MULTILINE | re.DOTALL)


def cumul(texts: Iterable[str]) -> list[str]:
    cum = ""
    out = []
    for text in texts:
        cum += text + "\n"
        out.append(cum)
    return out


readme_python_codeblocks = cumul(
    python_codeblocks(Path(__file__, "..", "..", "README.md").resolve().read_text())
)
readme_python_codeblocks_ids = range(1, len(readme_python_codeblocks) + 1)


@pytest.mark.parametrize("code", readme_python_codeblocks, ids=readme_python_codeblocks_ids)
def test_python_codeblock_functional(code: str, tmp_path: Path) -> None:
    code = "from arcparse import *\n" + code
    path = tmp_path / "code.py"
    path.write_text(code)

    subprocess.check_call(["python3", str(path)])
