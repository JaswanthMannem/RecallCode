from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from recallcode.database import Base
from recallcode.models import Attempt, Problem, Review, Topic


def test_database_workflow():
    # Use an isolated in-memory database for this test.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    Base.metadata.create_all(test_engine)

    try:
        with TestSession() as session:
            # Create a topic.
            topic = Topic(
                name="Subarrays",
                description="Contiguous portions of arrays",
            )
            session.add(topic)
            session.flush()

            # Save a problem under that topic.
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

            # Record an attempt.
            attempt = Attempt(
                problem=problem,
                outcome="solved_independently",
                used_hint=False,
                time_taken_minutes=20,
            )
            session.add(attempt)

            # Schedule a review.
            review = Review(
                problem=problem,
                due_at=datetime.now(UTC),
            )
            session.add(review)
            session.commit()

            # Verify saved data and relationships.
            saved_problem = session.scalar(
                select(Problem).where(Problem.title == "Maximum Subarray")
            )

            assert saved_problem is not None
            assert len(saved_problem.topics) == 1
            assert saved_problem.topics[0].name == "Subarrays"
            assert len(saved_problem.attempts) == 1
            assert len(saved_problem.reviews) == 1

            print("Database workflow test passed!")

    finally:
        Base.metadata.drop_all(test_engine)
        test_engine.dispose()
