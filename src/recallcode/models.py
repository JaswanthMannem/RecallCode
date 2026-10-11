from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recallcode.database import Base

problem_topics = Table(
    "problem_topics",
    Base.metadata,
    Column(
        "problem_id",
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "topic_id",
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id"), nullable=True
    )

    problems: Mapped[list["Problem"]] = relationship(
        secondary=problem_topics,
        back_populates="topics",
    )
    parent: Mapped["Topic | None"] = relationship(
        remote_side="Topic.id",
        back_populates="children",
    )
    children: Mapped[list["Topic"]] = relationship(back_populates="parent")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    aliases: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform: Mapped[str] = mapped_column(String(30), default="LeetCode")
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="attempted")
    approach: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    mistakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_complexity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    space_complexity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    topics: Mapped[list["Topic"]] = relationship(
        secondary=problem_topics,
        back_populates="problems",
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        index=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    outcome: Mapped[str] = mapped_column(String(30))
    used_hint: Mapped[bool] = mapped_column(default=False)
    time_taken_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    problem: Mapped["Problem"] = relationship(back_populates="attempts")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int | None] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    result: Mapped[str | None] = mapped_column(String(30), nullable=True)

    problem: Mapped["Problem | None"] = relationship(back_populates="reviews")
    topic: Mapped["Topic | None"] = relationship()
