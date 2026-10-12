from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from recallcode.database import SessionLocal
from recallcode.models import Topic


def create_topic(
    name: str,
    description: str | None = None,
    *,
    session_factory: sessionmaker = SessionLocal,
) -> int:
    """Create a topic and return its ID."""
    name = name.strip()
    if not name:
        raise ValueError("Topic name cannot be empty.")

    with session_factory.begin() as session:
        topic = Topic(name=name, description=description or None)
        session.add(topic)
        session.flush()
        topic_id = topic.id

    return topic_id


def list_topics(
    *,
    session_factory: sessionmaker = SessionLocal,
) -> list[tuple[int, str]]:
    """Return topic IDs and names, ordered alphabetically."""
    with session_factory() as session:
        topics = session.scalars(select(Topic).order_by(Topic.name)).all()
        return [(topic.id, topic.name) for topic in topics]


def list_topics_with_notes(
    *,
    session_factory: sessionmaker = SessionLocal,
) -> list[tuple[int, str, str | None]]:
    """Return topic IDs, names, and descriptions, ordered alphabetically."""
    with session_factory() as session:
        topics = session.scalars(select(Topic).order_by(Topic.name)).all()
        return [(topic.id, topic.name, topic.description) for topic in topics]
