from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from scripts.safe_plot import (
    UnsafePlotCode,
    _child_environment,
    safe_execute_plot_code,
    validate_plot_code,
)


class FakeVisualizer:
    _last_vector_paths: ClassVar[dict[str, str]] = {}

    @staticmethod
    def _ratio_to_dimensions(_ratio: str) -> tuple[int, int]:
        return 1200, 800


@pytest.mark.parametrize(
    "code",
    [
        "import os\nos.system('id')",
        "open('/tmp/leak', 'w').write('x')",
        "import socket\nsocket.create_connection(('example.com', 80))",
        "import pandas as pd\npd.read_csv('/etc/passwd')",
        "import matplotlib.pyplot as plt\nplt.savefig('/tmp/wrong.png')",
        "exec('print(1)')",
    ],
)
def test_rejects_unsafe_generated_code(code: str) -> None:
    with pytest.raises(UnsafePlotCode):
        validate_plot_code(code)


def test_accepts_normal_matplotlib_code() -> None:
    validate_plot_code(
        "import numpy as np\n"
        "import matplotlib.pyplot as plt\n"
        "x = np.array([1, 2, 3])\n"
        "plt.plot(x, x ** 2)\n"
        "plt.savefig(OUTPUT_PATH)\n"
    )


def test_child_environment_excludes_api_keys(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-child")
    monkeypatch.setenv("GOOGLE_API_KEY", "must-not-reach-child")
    environment = _child_environment(str(tmp_path))
    assert "OPENAI_API_KEY" not in environment
    assert "GOOGLE_API_KEY" not in environment


def test_executes_valid_plot_when_matplotlib_available(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    code = (
        "import matplotlib.pyplot as plt\n"
        "plt.plot([1, 2], [3, 4])\n"
        "plt.savefig(OUTPUT_PATH)\n"
    )
    output = tmp_path / "plot.png"
    assert safe_execute_plot_code(FakeVisualizer(), code, str(output))
    assert output.is_file()
