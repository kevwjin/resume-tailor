from __future__ import annotations

import re

LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(value: str | None) -> str:
    if not value:
        return ""
    return "".join(LATEX_REPLACEMENTS.get(char, char) for char in value)


def tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9+#.-]*", value.lower())


def keyword_set(value: str) -> set[str]:
    return {token for token in tokenize(value) if len(token) > 2}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "resume"
