from resume_tailor.text import latex_escape


def test_latex_escape_special_chars() -> None:
    assert latex_escape("A&B_100%") == r"A\&B\_100\%"
