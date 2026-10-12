import pytest

from recallcode.note_service import read_topic_notes, save_topic_notes
from recallcode.topic_service import create_topic


def make_topic(session_factory, name="Arrays"):
    return create_topic(name, session_factory=session_factory)


def test_new_topic_has_empty_notes(test_session_factory, tmp_path):
    topic_id = make_topic(test_session_factory)

    content = read_topic_notes(
        topic_id,
        session_factory=test_session_factory,
        notes_dir=tmp_path,
    )

    assert content == ""


def test_save_and_read_notes(test_session_factory, tmp_path):
    topic_id = make_topic(test_session_factory)
    content = "# Arrays\n\n- Two pointers\n- Sliding window\n"

    save_topic_notes(
        topic_id,
        content,
        session_factory=test_session_factory,
        notes_dir=tmp_path,
    )

    assert (
        read_topic_notes(
            topic_id,
            session_factory=test_session_factory,
            notes_dir=tmp_path,
        )
        == content
    )


def test_save_empty_notes(test_session_factory, tmp_path):
    topic_id = make_topic(test_session_factory)

    save_topic_notes(
        topic_id,
        "",
        session_factory=test_session_factory,
        notes_dir=tmp_path,
    )

    assert (
        read_topic_notes(
            topic_id,
            session_factory=test_session_factory,
            notes_dir=tmp_path,
        )
        == ""
    )


def test_saving_notes_creates_markdown_file(test_session_factory, tmp_path):
    topic_id = make_topic(test_session_factory)

    save_topic_notes(
        topic_id,
        "# Arrays",
        session_factory=test_session_factory,
        notes_dir=tmp_path,
    )

    files = list(tmp_path.glob("*.md"))

    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8") == "# Arrays"


def test_topics_have_separate_note_files(test_session_factory, tmp_path):
    arrays_id = make_topic(test_session_factory, "Arrays")
    trees_id = make_topic(test_session_factory, "Trees")

    save_topic_notes(
        arrays_id,
        "# Array notes",
        session_factory=test_session_factory,
        notes_dir=tmp_path,
    )
    save_topic_notes(
        trees_id,
        "# Tree notes",
        session_factory=test_session_factory,
        notes_dir=tmp_path,
    )

    assert (
        read_topic_notes(
            arrays_id,
            session_factory=test_session_factory,
            notes_dir=tmp_path,
        )
        == "# Array notes"
    )

    assert (
        read_topic_notes(
            trees_id,
            session_factory=test_session_factory,
            notes_dir=tmp_path,
        )
        == "# Tree notes"
    )

    assert len(list(tmp_path.glob("*.md"))) == 2


def test_read_notes_for_nonexistent_topic_raises(test_session_factory, tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        read_topic_notes(
            9999,
            session_factory=test_session_factory,
            notes_dir=tmp_path,
        )


def test_save_notes_for_nonexistent_topic_raises(test_session_factory, tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        save_topic_notes(
            9999,
            "# Missing topic",
            session_factory=test_session_factory,
            notes_dir=tmp_path,
        )


def test_save_notes_rejects_non_string_content(test_session_factory, tmp_path):
    topic_id = make_topic(test_session_factory)

    with pytest.raises(TypeError, match="must be text"):
        save_topic_notes(
            topic_id,
            None,
            session_factory=test_session_factory,
            notes_dir=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []


def test_topic_notes_path_is_saved(test_session_factory, tmp_path):
    topic_id = make_topic(test_session_factory)

    save_topic_notes(
        topic_id,
        "# Arrays",
        session_factory=test_session_factory,
        notes_dir=tmp_path,
    )

    from sqlalchemy import select

    from recallcode.models import Topic

    with test_session_factory() as session:
        topic = session.scalar(select(Topic).where(Topic.id == topic_id))
        assert topic is not None
        assert topic.notes_path == f"notes/{topic_id}.md"
