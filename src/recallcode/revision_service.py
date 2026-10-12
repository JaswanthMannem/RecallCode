from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload, sessionmaker

from recallcode.database import SessionLocal
from recallcode.models import Problem, Review, Topic

REVIEW_INTERVALS = {
    "remembered": 7,
    "partial": 3,
    "forgotten": 1,
}

VALID_RESULTS = set(REVIEW_INTERVALS)


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def create_review(
    *,
    due_at: datetime,
    problem_id: int | None = None,
    topic_id: int | None = None,
    session_factory: sessionmaker = SessionLocal,
) -> int:
    """Schedule a review for a problem or topic."""
    if (problem_id is None) == (topic_id is None):
        raise ValueError("Provide exactly one of problem_id or topic_id.")

    with session_factory.begin() as session:
        if problem_id is not None and session.get(Problem, problem_id) is None:
            raise ValueError(f"Problem {problem_id} does not exist.")

        if topic_id is not None and session.get(Topic, topic_id) is None:
            raise ValueError(f"Topic {topic_id} does not exist.")

        review = Review(
            problem_id=problem_id,
            topic_id=topic_id,
            due_at=due_at,
        )
        session.add(review)
        session.flush()
        review_id = review.id

    return review_id


def list_due_reviews(
    *,
    as_of: datetime | None = None,
    include_completed: bool = False,
    session_factory: sessionmaker = SessionLocal,
) -> list[Review]:
    """Return reviews due by as_of, including overdue reviews."""
    cutoff = as_of or _now()

    with session_factory() as session:
        query = (
            select(Review)
            .options(
                selectinload(Review.problem),
                selectinload(Review.topic),
            )
            .where(Review.due_at <= cutoff)
        )

        if not include_completed:
            query = query.where(Review.completed_at.is_(None))

        query = query.order_by(Review.due_at.asc())
        return list(session.scalars(query).all())


def complete_review(
    review_id: int,
    result: str,
    *,
    session_factory: sessionmaker = SessionLocal,
) -> int:
    """Complete a review and schedule its next occurrence.

    Returns the new review ID. The completed review is retained as history.
    """
    result = result.strip().lower()

    if result not in VALID_RESULTS:
        raise ValueError(
            f"Invalid result. Choose one of: {', '.join(sorted(VALID_RESULTS))}."
        )

    with session_factory.begin() as session:
        review = session.get(Review, review_id)

        if review is None:
            raise ValueError(f"Review {review_id} does not exist.")

        if review.completed_at is not None:
            raise ValueError(f"Review {review_id} is already completed.")

        now = _now()
        review.completed_at = now
        review.result = result

        next_review = Review(
            problem_id=review.problem_id,
            topic_id=review.topic_id,
            due_at=now + timedelta(days=REVIEW_INTERVALS[result]),
        )
        session.add(next_review)
        session.flush()
        next_review_id = next_review.id

    return next_review_id


def list_upcoming_reviews(
    *,
    days: int = 7,
    as_of: datetime | None = None,
    session_factory: sessionmaker = SessionLocal,
) -> list[Review]:
    """Return incomplete reviews due in the next given number of days."""
    if days < 0:
        raise ValueError("Days cannot be negative.")

    start = as_of or _now()
    end = start + timedelta(days=days)

    with session_factory() as session:
        query = (
            select(Review)
            .options(
                selectinload(Review.problem),
                selectinload(Review.topic),
            )
            .where(
                Review.completed_at.is_(None),
                Review.due_at > start,
                Review.due_at <= end,
            )
            .order_by(Review.due_at.asc())
        )

        return list(session.scalars(query).all())
