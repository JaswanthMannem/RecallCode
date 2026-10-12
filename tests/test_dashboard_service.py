from datetime import UTC, datetime, timedelta

from recallcode.dashboard_service import (
    get_dashboard_summary,
    get_recent_attempts,
    get_topic_progress,
)
from recallcode.problem_service import create_problem, record_attempt
from recallcode.revision_service import create_review
from recallcode.topic_service import create_topic


def test_empty_dashboard_summary(test_session_factory):
    summary = get_dashboard_summary(
        session_factory=test_session_factory,
    )

    assert summary["total_problems"] == 0
    assert summary["total_attempts"] == 0
    assert summary["total_reviews"] == 0
    assert summary["due_reviews"] == 0


def test_dashboard_summary_counts_problems_and_attempts(test_session_factory):
    topic_id = create_topic(
        "Arrays",
        session_factory=test_session_factory,
    )
    create_problem(
        "Two Sum",
        topic_ids=[topic_id],
        difficulty="Easy",
        session_factory=test_session_factory,
    )
    problem_id = create_problem(
        "3Sum",
        topic_ids=[topic_id],
        difficulty="Medium",
        session_factory=test_session_factory,
    )
    record_attempt(
        problem_id,
        "solved",
        session_factory=test_session_factory,
    )

    summary = get_dashboard_summary(
        session_factory=test_session_factory,
    )

    assert summary["total_problems"] == 2
    assert summary["total_attempts"] == 1
    assert summary["difficulty_counts"]["Easy"] == 1
    assert summary["difficulty_counts"]["Medium"] == 1


def test_topic_progress(test_session_factory):
    topic_id = create_topic(
        "Arrays",
        session_factory=test_session_factory,
    )
    problem_id = create_problem(
        "Two Sum",
        topic_ids=[topic_id],
        session_factory=test_session_factory,
    )

    from recallcode.problem_service import update_problem

    update_problem(
        problem_id,
        status="solved",
        session_factory=test_session_factory,
    )

    progress = get_topic_progress(
        session_factory=test_session_factory,
    )

    assert len(progress) == 1
    assert progress[0]["topic"] == "Arrays"
    assert progress[0]["total_problems"] == 1
    assert progress[0]["solved_problems"] == 1
    assert progress[0]["completion_percent"] == 100.0


def test_topic_without_problems_has_zero_progress(test_session_factory):
    create_topic(
        "Graphs",
        session_factory=test_session_factory,
    )

    progress = get_topic_progress(
        session_factory=test_session_factory,
    )

    assert progress[0]["total_problems"] == 0
    assert progress[0]["completion_percent"] == 0.0


def test_due_review_counts(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    create_review(
        problem_id=problem_id,
        due_at=datetime.now(UTC) - timedelta(days=2),
        session_factory=test_session_factory,
    )

    summary = get_dashboard_summary(
        session_factory=test_session_factory,
    )

    assert summary["total_reviews"] == 1
    assert summary["due_reviews"] == 1
    assert summary["overdue_reviews"] == 1


def test_recent_attempts(test_session_factory):
    problem_id = create_problem(
        "Two Sum",
        session_factory=test_session_factory,
    )
    record_attempt(
        problem_id,
        "solved",
        session_factory=test_session_factory,
    )

    attempts = get_recent_attempts(
        session_factory=test_session_factory,
    )

    assert len(attempts) == 1
    assert attempts[0].problem.title == "Two Sum"
