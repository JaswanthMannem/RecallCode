from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload, sessionmaker

from recallcode.database import SessionLocal
from recallcode.models import Attempt, Problem, Review, Topic


def get_dashboard_summary(
    *,
    session_factory: sessionmaker = SessionLocal,
) -> dict:
    """Return high-level problem, attempt, and revision statistics."""
    now = datetime.now(UTC)

    with session_factory() as session:
        total_problems = session.scalar(select(func.count(Problem.id))) or 0

        status_rows = session.execute(
            select(Problem.status, func.count(Problem.id)).group_by(Problem.status)
        ).all()
        status_counts = {status: count for status, count in status_rows}

        difficulty_rows = session.execute(
            select(Problem.difficulty, func.count(Problem.id)).group_by(
                Problem.difficulty
            )
        ).all()
        difficulty_counts = {
            difficulty or "Unspecified": count for difficulty, count in difficulty_rows
        }

        total_attempts = session.scalar(select(func.count(Attempt.id))) or 0

        total_reviews = session.scalar(select(func.count(Review.id))) or 0

        completed_reviews = (
            session.scalar(
                select(func.count(Review.id)).where(Review.completed_at.is_not(None))
            )
            or 0
        )

        due_reviews = (
            session.scalar(
                select(func.count(Review.id)).where(
                    Review.completed_at.is_(None),
                    Review.due_at <= now,
                )
            )
            or 0
        )

        overdue_reviews = (
            session.scalar(
                select(func.count(Review.id)).where(
                    Review.completed_at.is_(None),
                    Review.due_at < now - timedelta(days=1),
                )
            )
            or 0
        )

        return {
            "total_problems": total_problems,
            "status_counts": status_counts,
            "difficulty_counts": difficulty_counts,
            "total_attempts": total_attempts,
            "total_reviews": total_reviews,
            "completed_reviews": completed_reviews,
            "due_reviews": due_reviews,
            "overdue_reviews": overdue_reviews,
        }


def get_topic_progress(
    *,
    session_factory: sessionmaker = SessionLocal,
) -> list[dict]:
    """Return problem counts and status breakdowns for every topic."""
    with session_factory() as session:
        topics = session.scalars(
            select(Topic).options(selectinload(Topic.problems)).order_by(Topic.name)
        ).all()

        results = []

        for topic in topics:
            status_counts: dict[str, int] = {}

            for problem in topic.problems:
                status_counts[problem.status] = status_counts.get(problem.status, 0) + 1

            total = len(topic.problems)
            solved = status_counts.get("solved", 0)

            results.append(
                {
                    "topic_id": topic.id,
                    "topic": topic.name,
                    "total_problems": total,
                    "solved_problems": solved,
                    "status_counts": status_counts,
                    "completion_percent": (
                        round(solved / total * 100, 1) if total else 0.0
                    ),
                }
            )

        return results


def get_recent_attempts(
    *,
    limit: int = 10,
    session_factory: sessionmaker = SessionLocal,
) -> list[Attempt]:
    """Return the most recent attempts with their problem details."""
    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    with session_factory() as session:
        attempts = session.scalars(
            select(Attempt)
            .options(selectinload(Attempt.problem))
            .order_by(Attempt.attempted_at.desc(), Attempt.id.desc())
            .limit(limit)
        ).all()

        return list(attempts)
