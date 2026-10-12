import pytest
from sqlalchemy.exc import IntegrityError

from recallcode.topic_service import (
    create_topic,
    list_topics,
    list_topics_with_notes,
)


def test_create_topic(test_session_factory):
    topic_id = create_topic(
        "Arrays",
        "Contiguous sequence problems",
        session_factory=test_session_factory,
    )

    topics = list_topics(session_factory=test_session_factory)

    assert topics == [(topic_id, "Arrays")]


def test_create_topic_without_description(test_session_factory):
    topic_id = create_topic(
        "Strings",
        session_factory=test_session_factory,
    )

    topics = list_topics_with_notes(session_factory=test_session_factory)

    assert (topic_id, "Strings", None) in topics


def test_create_topic_trims_name(test_session_factory):
    topic_id = create_topic(
        "  Sliding Window  ",
        session_factory=test_session_factory,
    )

    assert list_topics(session_factory=test_session_factory) == [
        (topic_id, "Sliding Window")
    ]


@pytest.mark.parametrize("name", ["", "   ", "\t"])
def test_create_topic_rejects_empty_name(test_session_factory, name):
    with pytest.raises(ValueError, match="Topic name cannot be empty"):
        create_topic(name, session_factory=test_session_factory)

    assert list_topics(session_factory=test_session_factory) == []


def test_create_duplicate_topic_rejected(test_session_factory):
    create_topic("Arrays", session_factory=test_session_factory)

    with pytest.raises(IntegrityError):
        create_topic("Arrays", session_factory=test_session_factory)


def test_list_topics_is_alphabetical(test_session_factory):
    create_topic("Trees", session_factory=test_session_factory)
    create_topic("Arrays", session_factory=test_session_factory)
    create_topic("Graphs", session_factory=test_session_factory)

    names = [name for _, name in list_topics(session_factory=test_session_factory)]

    assert names == ["Arrays", "Graphs", "Trees"]


def test_list_topics_with_notes_includes_descriptions(test_session_factory):
    topic_id = create_topic(
        "Graphs",
        "Traversal and connectivity",
        session_factory=test_session_factory,
    )

    assert list_topics_with_notes(session_factory=test_session_factory) == [
        (topic_id, "Graphs", "Traversal and connectivity")
    ]
