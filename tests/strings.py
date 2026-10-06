from __future__ import annotations

import ast
import re
from html.parser import HTMLParser
from pathlib import Path

from tests.helpers import ROOT

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
WEB = ROOT / "voltplan" / "web"
SERVER_SKIP = {"consultant.py"}
ATTRIBUTES = {"title", "placeholder", "aria-label"}
JS_LITERAL = re.compile(r"'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`")
SINGLE = r"'(?:[^'\\\n]|\\.)*'"
JOINED = re.compile(rf"{SINGLE}(?:\s*\+\s*{SINGLE})+")
PART = re.compile(r"'((?:[^'\\\n]|\\.)*)'")
T_CALL = re.compile(r"\bt\('((?:[^'\\\n]|\\.)*)'")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip() if "\n" in text else text.strip()


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: set[str] = set()
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        for name, value in attrs:
            if name in ATTRIBUTES and value and CYRILLIC.search(value):
                self.found.add(clean(value))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and CYRILLIC.search(data):
            self.found.add(clean(data))


def html_strings() -> set[str]:
    found: set[str] = set()
    for path in sorted(WEB.glob("*.html")):
        page = Page()
        page.feed(path.read_text(encoding="utf-8"))
        found |= page.found
        title = re.search(r"<title>(.*?)</title>", path.read_text(encoding="utf-8"), re.S)
        if title:
            found.add(clean(title.group(1)))
    return found


def template(text: str) -> str:
    counter = iter(range(1, 100))
    return re.sub(r"\$\{[^}]*\}", lambda match: f"{{p{next(counter)}}}", text)


def js_strings() -> set[str]:
    found: set[str] = set()
    for path in sorted(WEB.glob("js/*.js")):
        if path.name == "i18n.js":
            continue
        text = path.read_text(encoding="utf-8")
        for called in T_CALL.findall(text):
            if CYRILLIC.search(called):
                found.add(clean(called.replace("\\'", "'")))
        for chain in JOINED.findall(text):
            joined = "".join(PART.findall(chain)).replace("\\'", "'")
            if CYRILLIC.search(joined):
                found.add(clean(joined))
        for single, backtick in JS_LITERAL.findall(text):
            value = single.replace("\\'", "'") if single else template(backtick)
            if CYRILLIC.search(value):
                found.add(clean(value))
    return found


class Constants(ast.NodeVisitor):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                self.values[node.targets[0].id] = value.value


def pattern(node, constants: dict[str, str], counter) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for piece in node.values:
            if isinstance(piece, ast.Constant):
                parts.append(str(piece.value))
            else:
                parts.append(f"{{p{next(counter)}}}")
        return "".join(parts)
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = pattern(node.left, constants, counter)
        right = pattern(node.right, constants, counter)
        if left is not None and right is not None:
            return left + right
    return None


def python_strings() -> set[str]:
    found: set[str] = set()
    for path in sorted((ROOT / "voltplan").rglob("*.py")):
        if path.name in SERVER_SKIP:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        collector = Constants()
        collector.visit(tree)
        inside_binop = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                value = pattern(node, collector.values, iter(range(1, 100)))
                if value and CYRILLIC.search(value):
                    found.add(value.strip())
                    inside_binop.update(id(child) for child in ast.walk(node))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant | ast.JoinedStr) and id(node) not in inside_binop:
                value = pattern(node, collector.values, iter(range(1, 100)))
                if value and CYRILLIC.search(value) and not (isinstance(node, ast.Constant)
                                                             and "\n" in value and len(value) > 300):
                    found.add(value.strip())
    return found


def all_strings() -> set[str]:
    return {item for item in html_strings() | js_strings() | python_strings() if item}


def dictionary_path(code: str) -> Path:
    return WEB / "i18n" / f"{code}.json"
