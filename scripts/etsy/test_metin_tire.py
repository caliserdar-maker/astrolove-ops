#!/usr/bin/env python3
"""Musteriye giden hedef metinlerde uzun ve orta tire bulunmadigini denetle."""

import ast
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
FORBIDDEN_DASHES = {"—", "–"}
PYTHON_TARGETS = {
    "etsy/pod_listing_create.py": {"SIZE_BLOCK_TXT", "MATERIALS", "size_block", "digital_lines"},
    "pod/factcheck.py": {"FACTS"},
    "etsy/xsell_links.py": {"RU_ONLY", "SPEC"},
    "pinterest/build_week_v2.py": {"TITLE_TPL", "DESC_TPL"},
}


def customer_strings(path, names):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    strings = []
    for node in tree.body:
        name = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(target, ast.Name):
                name = target.id
        if name in names:
            docstring_node = (
                node.body[0].value
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
                else None
            )
            strings.extend(
                child.value for child in ast.walk(node)
                if isinstance(child, ast.Constant)
                and isinstance(child.value, str)
                and child is not docstring_node
            )
    return strings


class CustomerTextTest(unittest.TestCase):
    def test_customer_text_has_no_forbidden_dashes(self):
        for relative_path, names in PYTHON_TARGETS.items():
            path = SCRIPTS / relative_path
            with self.subTest(path=relative_path):
                text = "\n".join(customer_strings(path, names))
                self.assertTrue(text, "Hedef musteri metni bulunamadi")
                self.assertTrue(FORBIDDEN_DASHES.isdisjoint(text))

        description = SCRIPTS / "etsy/desc/AQUARIUS_AQUARIUS_4570110121.txt"
        self.assertTrue(FORBIDDEN_DASHES.isdisjoint(description.read_text(encoding="utf-8")))

    def test_hahnemuhle_spelling(self):
        targets = [SCRIPTS / path for path in PYTHON_TARGETS]
        targets.append(SCRIPTS / "etsy/desc/AQUARIUS_AQUARIUS_4570110121.txt")
        for path in targets:
            with self.subTest(path=path.relative_to(SCRIPTS)):
                self.assertNotIn("Hahnemuhle", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
