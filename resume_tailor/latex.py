from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader

from resume_tailor.render import OUTPUT_BASENAME


class LatexError(RuntimeError):
    pass


def compile_pdf(tex_path: Path) -> Path:
    output_dir = tex_path.parent
    _clean_latex_state(output_dir)
    if shutil.which("latexmk"):
        cmd = ["latexmk", "-g", "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
    elif shutil.which("pdflatex"):
        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
    else:
        raise LatexError("Neither latexmk nor pdflatex is available on PATH.")

    result = subprocess.run(
        cmd,
        cwd=output_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise LatexError(result.stdout[-4000:])
    return output_dir / f"{OUTPUT_BASENAME}.pdf"


def page_count(pdf_path: Path) -> int:
    return len(PdfReader(str(pdf_path)).pages)


def has_overfull_hbox(tex_path: Path) -> bool:
    log_path = tex_path.with_suffix(".log")
    if not log_path.exists():
        return False
    return "Overfull \\hbox" in log_path.read_text(encoding="utf-8", errors="replace")


def _clean_latex_state(output_dir: Path) -> None:
    for suffix in [".aux", ".fdb_latexmk", ".fls", ".log", ".out"]:
        path = output_dir / f"{OUTPUT_BASENAME}{suffix}"
        if path.exists():
            path.unlink()
