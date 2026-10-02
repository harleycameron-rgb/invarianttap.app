import ast
from pathlib import Path


FORBIDDEN = ("cloudbeast", "burnharness", "sentinel_dot", "scandoc", "orrery")


def test_no_sibling_imports():
    root = Path(__file__).resolve().parents[1]
    # Application modules currently live at the root; tests use a reference verifier.
    sources = [*root.glob("*.py"), *(root / "invarianttap").rglob("*.py")]
    assert sources, "no application Python modules found"
    offenders = []
    for py in sources:
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if any(f in name.name.lower() for f in FORBIDDEN):
                        offenders.append((py, name.name))
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").lower()
                if any(f in module for f in FORBIDDEN):
                    offenders.append((py, node.module))
    assert not offenders, f"sibling imports found: {offenders}"
