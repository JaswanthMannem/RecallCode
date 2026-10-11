from sqlalchemy import select

from recallcode.database import SessionLocal
from recallcode.models import Topic


def create_topic(
    name: str,
    description: str | None = None,
) -> int:
    """Create a topic and return its ID."""
    name = name.strip()
    if not name:
        raise ValueError("Topic name cannot be empty.")

    with SessionLocal.begin() as session:
        topic = Topic(name=name, description=description or None)
        session.add(topic)
        session.flush()
        topic_id = topic.id

    return topic_id


def list_topics() -> list[tuple[int, str]]:
    """Return topic IDs and names, ordered alphabetically."""
    with SessionLocal() as session:
        topics = session.scalars(select(Topic).order_by(Topic.name)).all()

        return [(topic.id, topic.name) for topic in topics]
