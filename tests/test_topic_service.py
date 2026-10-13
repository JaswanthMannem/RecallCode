import pytest
from sqlalchemy.exc import IntegrityError

from recallcode.models import Problem, Review, Topic
from recallcode.problem_service import create_problem
from recallcode.topic_service import (
    create_topic,
    delete_topic,
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


def test_delete_topic_preserves_problems_and_removes_associations(
    test_session_factory,
):
    topic_id = create_topic(
        "Topic To Delete",
        session_factory=test_session_factory,
    )
    problem_id = create_problem(
        "Problem To Preserve",
        topic_ids=[topic_id],
        session_factory=test_session_factory,
    )

    assert delete_topic(topic_id, session_factory=test_session_factory) is True

    with test_session_factory() as session:
        assert session.get(Topic, topic_id) is None

        problem = session.get(Problem, problem_id)
        assert problem is not None
        assert all(topic.id != topic_id for topic in problem.topics)


def test_delete_topic_removes_topic_reviews(test_session_factory):
    from datetime import UTC, datetime

    from recallcode.revision_service import create_review

    topic_id = create_topic(
        "Review Topic To Delete",
        session_factory=test_session_factory,
    )
    review_id = create_review(
        topic_id=topic_id,
        due_at=datetime.now(UTC),
        session_factory=test_session_factory,
    )

    assert delete_topic(topic_id, session_factory=test_session_factory) is True

    with test_session_factory() as session:
        assert session.get(Review, review_id) is None


def test_delete_nonexistent_topic_returns_false(test_session_factory):
    assert delete_topic(999999, session_factory=test_session_factory) is False


def test_delete_topic_with_children_is_rejected(test_session_factory):
    parent_id = create_topic(
        "Parent Topic",
        session_factory=test_session_factory,
    )

    with test_session_factory.begin() as session:
        child = Topic(name="Child Topic", parent_id=parent_id)
        session.add(child)

    with pytest.raises(ValueError, match="child topics"):
        delete_topic(parent_id, session_factory=test_session_factory)

    with test_session_factory() as session:
        assert session.get(Topic, parent_id) is not None
