from datetime import UTC, datetime, timedelta

import pytest

from recallcode.models import Review
from recallcode.problem_service import create_problem
from recallcode.revision_service import (
    complete_review,
    create_review,
    list_due_reviews,
    list_upcoming_reviews,
)
from recallcode.topic_service import create_topic


def test_create_review_for_problem(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    due_at = datetime.now(UTC) - timedelta(days=1)

    review_id = create_review(
        problem_id=problem_id,
        due_at=due_at,
        session_factory=test_session_factory,
    )

    assert review_id > 0


def test_create_review_requires_exactly_one_target(test_session_factory):
    with pytest.raises(ValueError, match="exactly one"):
        create_review(
            due_at=datetime.now(UTC),
            session_factory=test_session_factory,
        )


def test_create_review_rejects_nonexistent_problem(test_session_factory):
    with pytest.raises(ValueError, match="does not exist"):
        create_review(
            problem_id=9999,
            due_at=datetime.now(UTC),
            session_factory=test_session_factory,
        )


def test_list_due_reviews_returns_incomplete_due_reviews(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    now = datetime.now(UTC)

    due_id = create_review(
        problem_id=problem_id,
        due_at=now - timedelta(hours=1),
        session_factory=test_session_factory,
    )
    create_review(
        problem_id=problem_id,
        due_at=now + timedelta(days=1),
        session_factory=test_session_factory,
    )

    reviews = list_due_reviews(
        as_of=now,
        session_factory=test_session_factory,
    )

    assert [review.id for review in reviews] == [due_id]


def test_complete_review_schedules_next_review(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    review_id = create_review(
        problem_id=problem_id,
        due_at=datetime.now(UTC) - timedelta(days=1),
        session_factory=test_session_factory,
    )

    next_id = complete_review(
        review_id,
        "remembered",
        session_factory=test_session_factory,
    )

    with test_session_factory() as session:
        completed = session.get(Review, review_id)
        next_review = session.get(Review, next_id)

        assert completed is not None
        assert completed.completed_at is not None
        assert completed.result == "remembered"

        assert next_review is not None
        assert next_review.problem_id == problem_id
        assert next_review.completed_at is None
        assert next_review.due_at >= completed.completed_at + timedelta(days=7)


def test_complete_review_rejects_invalid_result(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    review_id = create_review(
        problem_id=problem_id,
        due_at=datetime.now(UTC),
        session_factory=test_session_factory,
    )

    with pytest.raises(ValueError, match="Invalid result"):
        complete_review(
            review_id,
            "unknown",
            session_factory=test_session_factory,
        )


def test_complete_review_cannot_be_completed_twice(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    review_id = create_review(
        problem_id=problem_id,
        due_at=datetime.now(UTC),
        session_factory=test_session_factory,
    )

    complete_review(
        review_id,
        "partial",
        session_factory=test_session_factory,
    )

    with pytest.raises(ValueError, match="already completed"):
        complete_review(
            review_id,
            "remembered",
            session_factory=test_session_factory,
        )


def test_list_upcoming_reviews(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    now = datetime.now(UTC)

    upcoming_id = create_review(
        problem_id=problem_id,
        due_at=now + timedelta(days=2),
        session_factory=test_session_factory,
    )
    create_review(
        problem_id=problem_id,
        due_at=now + timedelta(days=10),
        session_factory=test_session_factory,
    )

    reviews = list_upcoming_reviews(
        days=7,
        as_of=now,
        session_factory=test_session_factory,
    )

    assert [review.id for review in reviews] == [upcoming_id]


def test_create_review_for_topic(test_session_factory):
    topic_id = create_topic(
        "Arrays",
        session_factory=test_session_factory,
    )

    review_id = create_review(
        topic_id=topic_id,
        due_at=datetime.now(UTC),
        session_factory=test_session_factory,
    )

    with test_session_factory() as session:
        review = session.get(Review, review_id)

        assert review is not None
        assert review.topic_id == topic_id
        assert review.problem_id is None


def test_create_review_rejects_both_targets(test_session_factory):
    topic_id = create_topic(
        "Arrays",
        session_factory=test_session_factory,
    )
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )

    with pytest.raises(ValueError, match="exactly one"):
        create_review(
            problem_id=problem_id,
            topic_id=topic_id,
            due_at=datetime.now(UTC),
            session_factory=test_session_factory,
        )
