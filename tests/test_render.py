from resume_tailor.assemble import ResumeSelection
from resume_tailor.models import Profile, Project
from resume_tailor.render import forgejo_note


def test_forgejo_note_only_for_selected_forgejo_url() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "forgejo": {"host": "git.example.com", "code": "js2026"},
        }
    )
    github = Project(id="gh", title="GitHub", url="https://github.com/a/b")
    forgejo = Project(id="fj", title="Forgejo", url="https://git.example.com/a/b")
    assert forgejo_note(profile, ResumeSelection([], [github], [], [], [])) is None
    note = forgejo_note(profile, ResumeSelection([], [forgejo], [], [], []))
    assert "js2026" in note
    assert note.startswith(r"\faExclamationCircle")
