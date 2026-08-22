"""Constrained executor for PaperBanana's model-generated Matplotlib code.

The upstream library executes generated plot code in a subprocess. This module
adds an AST allowlist, strips credentials from the child environment, uses an
isolated temporary working directory, and applies resource limits on POSIX.
It is defense in depth rather than a kernel security boundary.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


class UnsafePlotCode(ValueError):
    """Raised when generated code exceeds the plotting capability boundary."""


ALLOWED_IMPORTS = {
    "collections",
    "colorsys",
    "datetime",
    "decimal",
    "math",
    "matplotlib",
    "mpl_toolkits",
    "numpy",
    "pandas",
    "scipy",
    "seaborn",
    "statistics",
    "textwrap",
}

BLOCKED_NAMES = {
    "__builtins__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "exit",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "quit",
    "setattr",
    "vars",
    "__import__",
}

BLOCKED_ATTRIBUTES = {
    "chmod",
    "chown",
    "connect",
    "dump",
    "dumps",
    "eval",
    "exec",
    "fork",
    "fromfile",
    "glob",
    "imsave",
    "imwrite",
    "listdir",
    "load",
    "loads",
    "memmap",
    "open",
    "os",
    "popen",
    "post",
    "query",
    "read_csv",
    "read_excel",
    "read_json",
    "read_parquet",
    "read_pickle",
    "remove",
    "rename",
    "replace",
    "request",
    "rmdir",
    "run",
    "save",
    "socket",
    "spawn",
    "symlink",
    "system",
    "to_csv",
    "to_excel",
    "to_json",
    "to_parquet",
    "to_pickle",
    "unlink",
    "urlopen",
    "walk",
    "write_bytes",
    "write_image",
    "write_text",
}

PROTECTED_NAMES = {"OUTPUT_PATH", "VECTOR_PATH_SVG", "VECTOR_PATH_PDF"}
FORBIDDEN_NODES = (ast.AsyncFunctionDef, ast.Await, ast.ClassDef, ast.Global, ast.Nonlocal)


def _root_module(name: str) -> str:
    return name.split(".", 1)[0]


def _savefig_target(call: ast.Call) -> ast.AST | None:
    if call.args:
        return call.args[0]
    for keyword in call.keywords:
        if keyword.arg in {"fname", "filename"}:
            return keyword.value
    return None


def validate_plot_code(code: str) -> ast.Module:
    """Parse and reject code outside a data-to-Matplotlib capability."""
    if len(code.encode("utf-8")) > 50_000:
        raise UnsafePlotCode("generated plot code exceeds 50 KB")

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise UnsafePlotCode(f"invalid generated Python: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafePlotCode(f"forbidden syntax: {type(node).__name__}")

        if isinstance(node, ast.Import):
            for alias in node.names:
                if _root_module(alias.name) not in ALLOWED_IMPORTS:
                    raise UnsafePlotCode(f"import not allowed: {alias.name}")

        if isinstance(node, ast.ImportFrom) and (
            not node.module or _root_module(node.module) not in ALLOWED_IMPORTS
        ):
            raise UnsafePlotCode(f"import not allowed: {node.module or '<relative>'}")

        if isinstance(node, ast.Name) and (
            node.id in BLOCKED_NAMES or node.id.startswith("__")
        ):
            raise UnsafePlotCode(f"name not allowed: {node.id}")

        if isinstance(node, ast.Attribute) and (
            node.attr in BLOCKED_ATTRIBUTES or node.attr.startswith("_")
        ):
            raise UnsafePlotCode(f"attribute not allowed: {node.attr}")

        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in PROTECTED_NAMES:
                    raise UnsafePlotCode(f"assignment not allowed: {target.id}")

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "savefig"
        ):
            target = _savefig_target(node)
            if not isinstance(target, ast.Name) or target.id not in PROTECTED_NAMES:
                raise UnsafePlotCode("savefig must target an injected output path")

    return tree


def _resource_limits() -> None:
    """Apply child-process limits where the resource module is available."""
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
        resource.setrlimit(resource.RLIMIT_AS, (4_000_000_000, 4_000_000_000))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64_000_000, 64_000_000))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    except (ImportError, OSError, ValueError):
        return


def _child_environment(temp_dir: str) -> dict[str, str]:
    """Build a minimal environment that never forwards provider credentials."""
    return {
        "HOME": temp_dir,
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "MPLBACKEND": "Agg",
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
        "TMPDIR": temp_dir,
    }


def safe_execute_plot_code(
    visualizer,
    code: str,
    output_path: str,
    aspect_ratio: str | None = None,
    vector_formats: list[str] | None = None,
) -> bool:
    """Drop-in replacement for VisualizerAgent._execute_plot_code."""
    code = re.sub(r'^OUTPUT_PATH\s*=\s*["\'].*["\']\s*$', "", code, flags=re.MULTILINE)
    code = re.sub(r'^VECTOR_PATH_\w+\s*=\s*["\'].*["\']\s*$', "", code, flags=re.MULTILINE)

    try:
        validate_plot_code(code)
    except UnsafePlotCode:
        visualizer._last_vector_paths = {}
        return False

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    header = f'OUTPUT_PATH = {str(output)!r}\n'

    formats: dict[str, Path] = {}
    for fmt in vector_formats or []:
        if fmt not in {"svg", "pdf"}:
            continue
        path = output.with_suffix(f".{fmt}")
        formats[fmt] = path
        header += f'VECTOR_PATH_{fmt.upper()} = {str(path)!r}\n'

    if aspect_ratio:
        width, height = visualizer._ratio_to_dimensions(aspect_ratio)
        header += (
            "import matplotlib\n"
            f"matplotlib.rcParams['figure.figsize'] = [{width / 150:.1f}, {height / 150:.1f}]\n"
        )

    suffix = ""
    if formats:
        suffix = "\nimport matplotlib.pyplot as _pb_plt\n"
        for fmt in formats:
            suffix += (
                f"_pb_plt.savefig(VECTOR_PATH_{fmt.upper()}, format={fmt!r}, "
                "bbox_inches='tight')\n"
            )

    with tempfile.TemporaryDirectory(prefix="paperbanana-plot-sandbox-") as temp_dir:
        script = Path(temp_dir) / "plot.py"
        script.write_text(header + code + suffix, encoding="utf-8")
        environment = _child_environment(temp_dir)
        kwargs = {
            "capture_output": True,
            "cwd": temp_dir,
            "env": environment,
            "text": True,
            "timeout": 30,
        }
        if os.name == "posix":
            kwargs["preexec_fn"] = _resource_limits

        try:
            result = subprocess.run(
                [sys.executable, "-I", str(script)], check=False, **kwargs
            )
        except subprocess.TimeoutExpired:
            visualizer._last_vector_paths = {}
            return False

    if result.returncode != 0 or not output.is_file():
        visualizer._last_vector_paths = {}
        return False

    visualizer._last_vector_paths = {
        fmt: str(path) for fmt, path in formats.items() if path.is_file()
    }
    return True


def install_safe_plot_executor() -> None:
    """Patch the upstream visualizer before a PaperBanana pipeline is built."""
    from paperbanana.agents.visualizer import VisualizerAgent

    VisualizerAgent._execute_plot_code = safe_execute_plot_code
