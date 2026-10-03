from __future__ import annotations

import ast
import importlib.util
import io
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

from tests.helpers import ROOT

SKIP_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", "logs", ".git"}
LINE_LIMIT = 120


def files(*patterns: str) -> list[Path]:
    found = []
    for pattern in patterns:
        for path in ROOT.rglob(pattern):
            if not SKIP_PARTS.intersection(path.relative_to(ROOT).parts):
                found.append(path)
    return sorted(found)


def python_comments(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            problems.append(f"{token.start[0]}: {token.string}")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            problems.append(f"{node.lineno}: строка документации")
    return problems


REGEX_BEFORE = set("(,=:[!&|?{};+-*%<>~^")
REGEX_WORDS = {"return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do"}


def js_comments(text: str) -> list[int]:
    problems = []
    i, n, line = 0, len(text), 1
    last = ""
    word = ""
    template_depth = []
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == "\n":
            line += 1
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "/" and nxt == "/":
            problems.append(line)
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            problems.append(line)
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            line += text.count("\n", i, end)
            i = end
            continue
        if ch in "'\"":
            i += 1
            while i < n and text[i] != ch:
                i += 2 if text[i] == "\\" else 1
            i += 1
            last, word = ch, ""
            continue
        if ch == "`" or (ch == "}" and template_depth and template_depth[-1] == 0):
            if ch == "}":
                template_depth.pop()
            i += 1
            while i < n and text[i] != "`":
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "$" and i + 1 < n and text[i + 1] == "{":
                    template_depth.append(0)
                    i += 2
                    break
                if text[i] == "\n":
                    line += 1
                i += 1
            else:
                i += 1
            last, word = "`", ""
            continue
        if ch == "{" and template_depth:
            template_depth[-1] += 1
        elif ch == "}" and template_depth:
            template_depth[-1] -= 1
        if ch == "/" and (last == "" or last in REGEX_BEFORE or word in REGEX_WORDS):
            i += 1
            in_class = False
            while i < n:
                c = text[i]
                if c == "\\":
                    i += 2
                    continue
                if c == "[":
                    in_class = True
                elif c == "]":
                    in_class = False
                elif c == "/" and not in_class:
                    break
                i += 1
            i += 1
            while i < n and text[i].isalpha():
                i += 1
            last, word = "/", ""
            continue
        if ch.isalnum() or ch in "_$":
            start = i
            while i < n and (text[i].isalnum() or text[i] in "_$"):
                i += 1
            word = text[start:i]
            last = word[-1]
            continue
        last, word = ch, ""
        i += 1
    return problems


def css_comments(text: str) -> list[int]:
    problems = []
    quote = None
    for index, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "/" and text[index + 1:index + 2] == "*":
            problems.append(text.count("\n", 0, index) + 1)
    return problems


@pytest.mark.parametrize("path", files("*.py"), ids=lambda p: str(p.relative_to(ROOT)))
def test_python_has_no_comments(path):
    assert python_comments(path) == []


@pytest.mark.parametrize("path", files("*.js"), ids=lambda p: str(p.relative_to(ROOT)))
def test_javascript_has_no_comments(path):
    assert js_comments(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", files("*.css"), ids=lambda p: str(p.relative_to(ROOT)))
def test_css_has_no_comments(path):
    assert css_comments(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", files("*.html", "*.svg"), ids=lambda p: str(p.relative_to(ROOT)))
def test_markup_has_no_comments(path):
    assert "<!--" not in path.read_text(encoding="utf-8")


SETTINGS = files("*.toml", ".gitignore", ".gitattributes")


@pytest.mark.parametrize("path", SETTINGS, ids=lambda p: str(p.relative_to(ROOT)))
def test_settings_have_no_comments(path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("#")]
    assert lines == []


@pytest.mark.parametrize("path", files("*.bat", "*.cmd"), ids=lambda p: str(p.relative_to(ROOT)))
def test_batch_files_have_no_comments(path):
    text = path.read_bytes().decode("cp866", errors="replace")
    lines = [line for line in text.splitlines() if line.strip().lower().startswith(("rem", "::", "@rem"))]
    assert lines == []


@pytest.mark.parametrize("path", files("*.py", "*.js", "*.css", "*.html"), ids=lambda p: str(p.relative_to(ROOT)))
def test_lines_fit_limit(path):
    long = [i for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if len(line) > LINE_LIMIT]
    assert long == []


@pytest.mark.skipif(importlib.util.find_spec("ruff") is None, reason="ruff не установлен")
def test_python_follows_pep8():
    result = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", "voltplan", "linecapacity", "tests"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("sample, expected", [
    ("const a = 1;", []),
    ("const a = 1; // тест", [1]),
    ("/* блок */\nconst b = 2;", [1]),
    ("const s = 'http://x';", []),
    ("const t = `a ${b} // не комментарий`;", []),
    ("const r = /\\/\\//g; const x = 4 / 2;", []),
    ("return a\n/* два */", [2]),
])
def test_javascript_detector(sample, expected):
    assert js_comments(sample) == expected


def test_python_detector(tmp_path):
    bad = tmp_path / "x.py"
    bad.write_text('def f():\n    """док"""\n    return 1  # шум\n', encoding="utf-8")
    assert len(python_comments(bad)) == 2
