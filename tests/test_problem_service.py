import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from recallcode.database import Base
from recallcode.models import Attempt, Problem, Review, Topic
from recallcode.problem_service import (
    create_problem,
    delete_problem,
    list_problems,
    record_attempt,
    update_problem,
)


@pytest.fixture
def session_factory():
    """Create an isolated in-memory database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    yield TestingSessionLocal

    engine.dispose()


@pytest.fixture
def topic_ids(session_factory):
    """Create reusable topics for tests."""
    with session_factory.begin() as session:
        arrays = Topic(name="Arrays")
        sorting = Topic(name="Sorting")
        strings = Topic(name="Strings")

        session.add_all([arrays, sorting, strings])
        session.flush()

        ids = {
            "arrays": arrays.id,
            "sorting": sorting.id,
            "strings": strings.id,
        }

    return ids


def test_create_and_list_problem(session_factory):
    problem_id = create_problem(
        title="Two Sum",
        platform="LeetCode",
        difficulty="Easy",
        session_factory=session_factory,
    )

    problems = list_problems(session_factory=session_factory)

    assert len(problems) == 1
    assert problems[0].id == problem_id
    assert problems[0].title == "Two Sum"
    assert problems[0].platform == "LeetCode"
    assert problems[0].difficulty == "Easy"


def test_filter_problems_by_platform(session_factory):
    create_problem(
        title="Two Sum",
        platform="LeetCode",
        session_factory=session_factory,
    )
    create_problem(
        title="Another Problem",
        platform="Codeforces",
        session_factory=session_factory,
    )

    problems = list_problems(
        platform="LeetCode",
        session_factory=session_factory,
    )

    assert len(problems) == 1
    assert problems[0].title == "Two Sum"


def test_create_problem_with_multiple_topics(
    session_factory,
    topic_ids,
):
    problem_id = create_problem(
        title="Sort Colors",
        topic_ids=[
            topic_ids["arrays"],
            topic_ids["sorting"],
        ],
        session_factory=session_factory,
    )

    problems = list_problems(session_factory=session_factory)

    assert len(problems) == 1
    assert problems[0].id == problem_id

    assigned_topics = {topic.name for topic in problems[0].topics}

    assert assigned_topics == {"Arrays", "Sorting"}


def test_filter_problems_by_topic(session_factory, topic_ids):
    create_problem(
        title="Sort Colors",
        topic_ids=[topic_ids["arrays"], topic_ids["sorting"]],
        session_factory=session_factory,
    )
    create_problem(
        title="Reverse String",
        topic_ids=[topic_ids["strings"]],
        session_factory=session_factory,
    )

    array_problems = list_problems(
        topic_id=topic_ids["arrays"],
        session_factory=session_factory,
    )
    sorting_problems = list_problems(
        topic_id=topic_ids["sorting"],
        session_factory=session_factory,
    )
    string_problems = list_problems(
        topic_id=topic_ids["strings"],
        session_factory=session_factory,
    )

    assert [problem.title for problem in array_problems] == ["Sort Colors"]
    assert [problem.title for problem in sorting_problems] == ["Sort Colors"]
    assert [problem.title for problem in string_problems] == ["Reverse String"]


def test_search_problem_by_title(session_factory):
    create_problem(
        title="Longest Substring Without Repeating Characters",
        session_factory=session_factory,
    )

    results = list_problems(
        search="Substring",
        session_factory=session_factory,
    )

    assert len(results) == 1
    assert results[0].title == "Longest Substring Without Repeating Characters"


def test_search_problem_by_alias(session_factory):
    create_problem(
        title="Sort Colors",
        aliases="Color Sort, Dutch National Flag",
        session_factory=session_factory,
    )

    results = list_problems(
        search="color sort",
        session_factory=session_factory,
    )

    assert len(results) == 1
    assert results[0].title == "Sort Colors"


def test_search_problem_by_another_alias(session_factory):
    create_problem(
        title="Sort Colors",
        aliases="Color Sort, Dutch National Flag",
        session_factory=session_factory,
    )

    results = list_problems(
        search="Dutch National Flag",
        session_factory=session_factory,
    )

    assert len(results) == 1
    assert results[0].title == "Sort Colors"


def test_search_is_case_insensitive(session_factory):
    create_problem(
        title="Sort Colors",
        aliases="Color Sort",
        session_factory=session_factory,
    )

    results = list_problems(
        search="COLOR SORT",
        session_factory=session_factory,
    )

    assert len(results) == 1
    assert results[0].title == "Sort Colors"


def test_update_problem(session_factory):
    problem_id = create_problem(
        title="Old Title",
        session_factory=session_factory,
    )

    updated = update_problem(
        problem_id,
        title="New Title",
        difficulty="Medium",
        session_factory=session_factory,
    )

    problems = list_problems(session_factory=session_factory)

    assert updated is True
    assert problems[0].title == "New Title"
    assert problems[0].difficulty == "Medium"


def test_update_problem_topics(session_factory, topic_ids):
    problem_id = create_problem(
        title="Sort Colors",
        topic_ids=[topic_ids["arrays"]],
        session_factory=session_factory,
    )

    updated = update_problem(
        problem_id,
        topic_ids=[topic_ids["sorting"], topic_ids["strings"]],
        session_factory=session_factory,
    )

    problems = list_problems(session_factory=session_factory)
    assigned_topics = {topic.name for topic in problems[0].topics}

    assert updated is True
    assert assigned_topics == {"Sorting", "Strings"}


def test_update_problem_aliases(session_factory):
    problem_id = create_problem(
        title="Sort Colors",
        session_factory=session_factory,
    )

    update_problem(
        problem_id,
        aliases="Color Sort",
        session_factory=session_factory,
    )

    results = list_problems(
        search="color sort",
        session_factory=session_factory,
    )

    assert len(results) == 1
    assert results[0].id == problem_id


def test_record_attempt(session_factory):
    problem_id = create_problem(
        title="Two Sum",
        session_factory=session_factory,
    )

    record_attempt(
        problem_id=problem_id,
        outcome="solved",
        time_taken_minutes=15,
        notes="Used a hash map",
        session_factory=session_factory,
    )

    with session_factory() as session:
        attempts = session.query(Attempt).all()

    assert len(attempts) == 1
    assert attempts[0].problem_id == problem_id
    assert attempts[0].outcome == "solved"
    assert attempts[0].time_taken_minutes == 15
    assert attempts[0].notes == "Used a hash map"


def test_record_multiple_attempts(session_factory):
    problem_id = create_problem(
        title="Two Sum",
        session_factory=session_factory,
    )

    record_attempt(
        problem_id=problem_id,
        outcome="failed",
        time_taken_minutes=20,
        session_factory=session_factory,
    )
    record_attempt(
        problem_id=problem_id,
        outcome="solved",
        time_taken_minutes=10,
        session_factory=session_factory,
    )

    with session_factory() as session:
        attempts = session.query(Attempt).all()

    assert len(attempts) == 2


def test_delete_problem(session_factory):
    problem_id = create_problem(
        title="Two Sum",
        session_factory=session_factory,
    )

    deleted = delete_problem(
        problem_id,
        session_factory=session_factory,
    )

    assert deleted is True
    assert list_problems(session_factory=session_factory) == []


def test_delete_problem_cascades_to_attempts_and_reviews(
    session_factory,
    topic_ids,
):
    from datetime import UTC, datetime

    problem_id = create_problem(
        title="Two Sum",
        topic_ids=[topic_ids["arrays"]],
        session_factory=session_factory,
    )

    with session_factory.begin() as session:
        session.add(
            Attempt(
                problem_id=problem_id,
                outcome="solved_independently",
                used_hint=False,
                time_taken_minutes=10,
            )
        )
        session.add(
            Review(
                problem_id=problem_id,
                due_at=datetime.now(UTC),
            )
        )

    deleted = delete_problem(
        problem_id,
        session_factory=session_factory,
    )

    assert deleted is True

    with session_factory() as session:
        assert session.query(Problem).count() == 0
        assert session.query(Attempt).count() == 0
        assert session.query(Review).count() == 0


def test_create_problem_rejects_empty_title(session_factory):
    with pytest.raises(ValueError):
        create_problem(
            title="   ",
            session_factory=session_factory,
        )


def test_create_problem_rejects_invalid_topic_id(session_factory):
    with pytest.raises(ValueError):
        create_problem(
            title="Sort Colors",
            topic_ids=[9999],
            session_factory=session_factory,
        )


def test_create_problem_rejects_mixed_valid_and_invalid_topic_ids(
    session_factory,
    topic_ids,
):
    with pytest.raises(ValueError):
        create_problem(
            title="Sort Colors",
            topic_ids=[topic_ids["arrays"], 9999],
            session_factory=session_factory,
        )


def test_update_rejects_invalid_field(session_factory):
    problem_id = create_problem(
        title="Two Sum",
        session_factory=session_factory,
    )

    with pytest.raises(ValueError):
        update_problem(
            problem_id,
            unknown_field="value",
            session_factory=session_factory,
        )


def test_record_attempt_rejects_negative_time(session_factory):
    problem_id = create_problem(
        title="Two Sum",
        session_factory=session_factory,
    )

    with pytest.raises(ValueError):
        record_attempt(
            problem_id=problem_id,
            outcome="solved",
            time_taken_minutes=-5,
            session_factory=session_factory,
        )


def test_record_attempt_rejects_nonexistent_problem(session_factory):
    with pytest.raises(ValueError):
        record_attempt(
            problem_id=9999,
            outcome="solved",
            time_taken_minutes=10,
            session_factory=session_factory,
        )
