"""Cross-reference self.<name> usage against definitions in src/UI/.

Scans every .py file in src/UI/ and checks that callback references
like on_xxx=self.<name> actually point to existing methods or attributes
on the same class.  Exits 0 if clean, 1 if issues found.

Usage:
    python scripts/validate_wiring.py [--path src/UI]
"""

import ast
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple


class Issue(NamedTuple):
    file: str
    line: int
    msg: str


def _py_files(root: Path) -> Iterator[Path]:
    for p in root.rglob("*.py"):
        if p.name == "__init__.py":
            continue
        yield p


def _methods_and_attrs(tree: ast.Module) -> dict[str, set[str]]:
    """Return {class_name: {method1, method2, attr1, ...}}."""
    result: dict[str, set[str]] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            names: set[str] = set()
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef):
                    names.add(item.name)
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                        ):
                            names.add(target.attr)
            result[node.name] = names
    return result


def _callback_refs(
    tree: ast.Module, file: str
) -> list[Issue]:
    """Find on_<event>=self.<name> refs where <name> is missing."""
    class_defs = {
        n.name: n
        for n in ast.iter_child_nodes(tree)
        if isinstance(n, ast.ClassDef)
    }
    classes = _methods_and_attrs(tree)
    issues: list[Issue] = []

    for cls_name, cls_node in class_defs.items():
        defined = classes.get(cls_name, set())

        for node in ast.walk(cls_node):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg is None or not kw.arg.startswith("on_"):
                    continue
                if _is_self_attr(kw.value):
                    attr_name = kw.value.attr
                    if attr_name not in defined:
                        issues.append(
                            Issue(
                                file,
                                kw.value.lineno,
                                f"{cls_name}: callback '{attr_name}' "
                                f"referenced via on_{kw.arg[3:]}="
                                f"{attr_name} but never defined",
                            )
                        )

    return issues


def _is_self_attr(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "src" / "UI"
    if "--path" in sys.argv:
        idx = sys.argv.index("--path")
        root = Path(sys.argv[idx + 1])

    if not root.is_dir():
        print(f"Error: {root} not found", file=sys.stderr)
        return 1

    all_issues: list[Issue] = []
    for py in _py_files(root):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError as e:
            print(f"Syntax error in {py}: {e}", file=sys.stderr)
            all_issues.append(Issue(str(py), e.lineno or 0, "syntax error"))
            continue
        rel = py.relative_to(root.parent.parent)
        all_issues.extend(_callback_refs(tree, str(rel)))

    if not all_issues:
        print("All wiring checks passed.")
        return 0

    for iss in all_issues:
        print(f"{iss.file}:{iss.line}: {iss.msg}")
    print(f"\n{len(all_issues)} wiring issue(s) found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
