from pathlib import Path

from sqlalchemy.orm import sessionmaker

from recallcode.database import SessionLocal
from recallcode.models import Topic

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NOTES_DIR = PROJECT_ROOT / "notes"


def _get_notes_path(
    topic_id: int,
    *,
    session_factory: sessionmaker = SessionLocal,
    notes_dir: Path = NOTES_DIR,
) -> Path:
    """Resolve a topic's Markdown file safely inside the notes directory."""
    with session_factory.begin() as session:
        topic = session.get(Topic, topic_id)

        if topic is None:
            raise ValueError(f"Topic with ID {topic_id} does not exist.")

        if not topic.notes_path:
            topic.notes_path = str(Path("notes") / f"{topic.id}.md")

        relative_path = Path(topic.notes_path)

    if relative_path.is_absolute():
        raise ValueError("Topic notes path must be relative.")

    # Use the configured notes directory, including for isolated tests.
    path = (notes_dir / relative_path.name).resolve()
    safe_root = notes_dir.resolve()

    if not path.is_relative_to(safe_root):
        raise ValueError("Topic notes path must stay inside the notes directory.")

    return path


def read_topic_notes(
    topic_id: int,
    *,
    session_factory: sessionmaker = SessionLocal,
    notes_dir: Path = NOTES_DIR,
) -> str:
    """Read a topic's Markdown notes, returning empty text if none exist."""
    path = _get_notes_path(
        topic_id,
        session_factory=session_factory,
        notes_dir=notes_dir,
    )

    if not path.exists():
        return ""

    if not path.is_file():
        raise ValueError("Topic notes path is not a file.")

    return path.read_text(encoding="utf-8")


def save_topic_notes(
    topic_id: int,
    content: str,
    *,
    session_factory: sessionmaker = SessionLocal,
    notes_dir: Path = NOTES_DIR,
) -> None:
    """Save Markdown notes for a topic."""
    if not isinstance(content, str):
        raise TypeError("Note content must be text.")

    path = _get_notes_path(
        topic_id,
        session_factory=session_factory,
        notes_dir=notes_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
