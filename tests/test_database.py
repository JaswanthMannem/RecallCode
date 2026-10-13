from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from recallcode.database import Base
from recallcode.models import Attempt, Problem, Review, Topic


def test_database_workflow():
    """Verify creating and retrieving related database records."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        """Enable foreign-key enforcement for this test database."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestSession = sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    Base.metadata.create_all(test_engine)

    try:
        with TestSession() as session:
            topic = Topic(
                name="Subarrays",
                description="Contiguous portions of arrays",
            )
            session.add(topic)
            session.flush()

            problem = Problem(
                title="Maximum Subarray",
                platform="LeetCode",
                difficulty="Medium",
                status="solved",
                topics=[topic],
                time_complexity="O(n)",
                space_complexity="O(1)",
            )
            session.add(problem)
            session.flush()

            attempt = Attempt(
                problem=problem,
                outcome="solved_independently",
                used_hint=False,
                time_taken_minutes=20,
            )
            session.add(attempt)

            review = Review(
                problem=problem,
                due_at=datetime.now(UTC),
            )
            session.add(review)
            session.commit()

            saved_problem = session.scalar(
                select(Problem).where(Problem.title == "Maximum Subarray")
            )

            assert saved_problem is not None
            assert len(saved_problem.topics) == 1
            assert saved_problem.topics[0].name == "Subarrays"
            assert len(saved_problem.attempts) == 1
            assert len(saved_problem.reviews) == 1

    finally:
        Base.metadata.drop_all(test_engine)
        test_engine.dispose()


def test_database_rejects_invalid_foreign_key(test_session_factory):
    """Verify that attempts cannot reference nonexistent problems."""
    with pytest.raises(IntegrityError), test_session_factory.begin() as session:
        session.add(
            Attempt(
                problem_id=999999,
                outcome="solved_independently",
            )
        )
        session.flush()
