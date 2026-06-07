from resume_tailor.latex import has_overfull_hbox


def test_has_overfull_hbox_reads_latex_log(tmp_path) -> None:
    tex_path = tmp_path / "resume.tex"
    tex_path.write_text("", encoding="utf-8")
    tex_path.with_suffix(".log").write_text(
        "Overfull \\hbox (22.23837pt too wide) in alignment at lines 127--127",
        encoding="utf-8",
    )

    assert has_overfull_hbox(tex_path)


def test_has_overfull_hbox_missing_log_is_false(tmp_path) -> None:
    assert not has_overfull_hbox(tmp_path / "resume.tex")
