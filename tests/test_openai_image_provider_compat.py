import ast
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (ROOT / "scripts" / "generate.py", ROOT / "scripts" / "plot.py")


def load_script(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenAIImageProviderCompatibilityTests(unittest.TestCase):
    def test_aspect_ratio_overrides_dimensions(self):
        for path in SCRIPTS:
            with self.subTest(script=path.name):
                module = load_script(path)
                self.assertEqual(module._resolve_dimensions(1024, 1024, "16:9"), (16.0, 9.0))
                self.assertEqual(module._resolve_dimensions(1024, 1024, "3:4"), (3.0, 4.0))

    def test_invalid_aspect_ratio_preserves_dimensions(self):
        for path in SCRIPTS:
            with self.subTest(script=path.name):
                module = load_script(path)
                self.assertEqual(module._resolve_dimensions(1024, 768, "invalid"), (1024, 768))
                self.assertEqual(module._resolve_dimensions(1024, 768, "0:9"), (1024, 768))

    def test_openai_generate_accepts_current_and_future_pipeline_kwargs(self):
        for path in SCRIPTS:
            with self.subTest(script=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                image_class = next(
                    node for node in ast.walk(tree)
                    if isinstance(node, ast.ClassDef) and node.name == "OpenAIImageGen"
                )
                generate = next(
                    node for node in image_class.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "generate"
                )
                parameters = [arg.arg for arg in generate.args.args]
                self.assertIn("aspect_ratio", parameters)
                self.assertIsNotNone(generate.args.kwarg)


if __name__ == "__main__":
    unittest.main()
