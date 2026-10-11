from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload, sessionmaker

from recallcode.database import SessionLocal
from recallcode.models import Attempt, Problem, Topic


def create_problem(
    title: str,
    platform: str = "LeetCode",
    url: str | None = None,
    difficulty: str | None = None,
    topic_ids: list[int] | None = None,
    aliases: str = "",
    *,
    session_factory: sessionmaker = SessionLocal,
) -> int:
    """Create a problem with optional aliases and multiple topics."""
    title = title.strip()
    if not title:
        raise ValueError("Problem title cannot be empty.")

    with session_factory.begin() as session:
        topics = []

        if topic_ids:
            unique_ids = set(topic_ids)
            topics = list(
                session.scalars(select(Topic).where(Topic.id.in_(unique_ids))).all()
            )

            if len(topics) != len(unique_ids):
                raise ValueError("One or more selected topics do not exist.")

        problem = Problem(
            title=title,
            platform=platform,
            url=url.strip() or None if url else None,
            difficulty=difficulty,
            aliases=aliases.strip(),
            topics=topics,
        )
        session.add(problem)
        session.flush()
        problem_id = problem.id

    return problem_id


def list_problems(
    topic_id: int | None = None,
    platform: str | None = None,
    search: str | None = None,
    *,
    session_factory: sessionmaker = SessionLocal,
) -> list[Problem]:
    """List problems with optional topic, platform, and text filters."""
    with session_factory() as session:
        query = select(Problem).options(selectinload(Problem.topics))

        if topic_id is not None:
            query = query.where(Problem.topics.any(Topic.id == topic_id))

        if platform:
            query = query.where(Problem.platform == platform)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Problem.title.ilike(term),
                    Problem.aliases.ilike(term),
                )
            )

        query = query.order_by(Problem.created_at.desc())
        return list(session.scalars(query).all())


def update_problem(
    problem_id: int,
    *,
    session_factory: sessionmaker = SessionLocal,
    **fields: object,
) -> bool:
    """Update editable problem fields, including topic assignments."""
    allowed_fields = {
        "title",
        "aliases",
        "url",
        "platform",
        "difficulty",
        "status",
        "approach",
        "key_observation",
        "mistakes",
        "time_complexity",
        "space_complexity",
        "topic_ids",
    }

    invalid_fields = set(fields) - allowed_fields
    if invalid_fields:
        raise ValueError(f"Unsupported fields: {sorted(invalid_fields)}")

    if "title" in fields:
        title = fields["title"]
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Problem title cannot be empty.")
        fields["title"] = title.strip()

    if "topic_ids" in fields:
        topic_ids = fields.pop("topic_ids")
        if not isinstance(topic_ids, list):
            raise ValueError("topic_ids must be a list of topic IDs.")

        unique_ids = set(topic_ids)

        with session_factory.begin() as session:
            problem = session.get(Problem, problem_id)
            if problem is None:
                return False

            topics = (
                list(
                    session.scalars(select(Topic).where(Topic.id.in_(unique_ids))).all()
                )
                if unique_ids
                else []
            )

            if len(topics) != len(unique_ids):
                raise ValueError("One or more selected topics do not exist.")

            problem.topics = topics

            for field, value in fields.items():
                setattr(problem, field, value)

        return True

    with session_factory.begin() as session:
        problem = session.get(Problem, problem_id)
        if problem is None:
            return False

        for field, value in fields.items():
            setattr(problem, field, value)

    return True


def delete_problem(
    problem_id: int,
    *,
    session_factory: sessionmaker = SessionLocal,
) -> bool:
    """Delete a problem and its dependent attempts and reviews."""
    with session_factory.begin() as session:
        problem = session.get(Problem, problem_id)

        if problem is None:
            return False

        session.delete(problem)

    return True


def record_attempt(
    problem_id: int,
    outcome: str,
    used_hint: bool = False,
    time_taken_minutes: int | None = None,
    notes: str | None = None,
    *,
    session_factory: sessionmaker = SessionLocal,
) -> int:
    """Record an attempt without overwriting previous attempts."""
    if time_taken_minutes is not None and time_taken_minutes < 0:
        raise ValueError("Time taken cannot be negative.")

    with session_factory.begin() as session:
        if session.get(Problem, problem_id) is None:
            raise ValueError(f"Problem {problem_id} does not exist.")

        attempt = Attempt(
            problem_id=problem_id,
            outcome=outcome,
            used_hint=used_hint,
            time_taken_minutes=time_taken_minutes,
            notes=notes,
        )
        session.add(attempt)
        session.flush()
        attempt_id = attempt.id

    return attempt_id
