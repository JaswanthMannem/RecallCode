from datetime import UTC, datetime, timedelta

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from recallcode.problem_service import list_problems
from recallcode.revision_service import (
    complete_review,
    create_review,
    list_due_reviews,
    list_upcoming_reviews,
)
from recallcode.topic_service import list_topics_with_notes

st.set_page_config(
    page_title="Revision Queue | RecallCode",
    page_icon="🔁",
    layout="wide",
)

st.title("🔁 Revision Queue")
st.caption("Practice active recall and keep your DSA knowledge fresh.")

# -------------------- Helpers --------------------


def describe_review(review):
    """Return a readable title and context for a review."""
    if review.problem is not None:
        return review.problem.title, "Problem"

    if review.topic is not None:
        return review.topic.name, "Topic"

    return "Unknown item", "Unknown"


def render_review_notes(review):
    """Show useful recall cues for a problem or topic."""
    if review.problem is not None:
        problem = review.problem

        if problem.key_observation:
            st.markdown("**Key observation**")
            st.write(problem.key_observation)

        with st.expander("Reveal approach and mistakes"):
            st.markdown("**Approach**")
            st.write(problem.approach or "No approach recorded.")

            st.markdown("**Mistakes**")
            st.write(problem.mistakes or "No mistakes recorded.")

            st.caption(
                f"Time: {problem.time_complexity or 'Not recorded'}"
                f" | Space: {problem.space_complexity or 'Not recorded'}"
            )

        if problem.url:
            st.markdown(f"[Open original problem]({problem.url})")

    elif review.topic is not None:
        st.caption(
            "Open the Topic Knowledge Base to revise this topic's Markdown notes."
        )


def render_review_card(review):
    """Display a review and allow the user to record recall quality."""
    title, item_type = describe_review(review)

    with st.container(border=True):
        st.markdown(f"### {title}")
        st.caption(f"{item_type} · Due {review.due_at:%d %b %Y, %H:%M UTC}")

        render_review_notes(review)

        st.markdown("**How well did you remember it?**")

        col1, col2, col3 = st.columns(3)

        outcomes = [
            (col1, "Remembered", "remembered"),
            (col2, "Partially", "partial"),
            (col3, "Forgot", "forgotten"),
        ]

        for column, label, result in outcomes:
            with column:
                if st.button(
                    label,
                    key=f"review_{review.id}_{result}",
                    use_container_width=True,
                ):
                    try:
                        complete_review(review.id, result)
                        st.session_state["revision_message"] = (
                            f"Recorded '{label.lower()}' for {title}. "
                            "The next review has been scheduled."
                        )
                        st.rerun()
                    except (ValueError, SQLAlchemyError) as exc:
                        st.error(f"Could not complete review: {exc}")


# -------------------- Status message --------------------

if message := st.session_state.pop("revision_message", None):
    st.success(message)

# -------------------- Queue summary --------------------

try:
    due_reviews = list_due_reviews()
    upcoming_reviews = list_upcoming_reviews(days=7)
except SQLAlchemyError:
    st.error("Could not load the revision queue from the database.")
    st.stop()

overdue_count = sum(review.due_at < datetime.now(UTC) for review in due_reviews)
due_today_count = len(due_reviews) - overdue_count

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Due now", len(due_reviews))
metric2.metric("Overdue", overdue_count)
metric3.metric("Upcoming (7 days)", len(upcoming_reviews))

st.divider()

# -------------------- Due reviews --------------------

st.subheader("Due for revision")

if not due_reviews:
    st.success("You're all caught up! No reviews are due right now.")
else:
    st.caption(
        f"{due_today_count} due today or recently scheduled; {overdue_count} overdue."
    )

    for review in due_reviews:
        render_review_card(review)

# -------------------- Schedule a first review --------------------

st.divider()
st.subheader("Schedule a review")

st.write("Add an existing problem or topic to your revision queue.")

schedule_type = st.radio(
    "What would you like to revise?",
    ["Problem", "Topic"],
    horizontal=True,
)

if schedule_type == "Problem":
    problems = list_problems()

    if not problems:
        st.info("Add a problem in Problem Journal first.")
    else:
        problem_options = {
            f"{problem.title} (ID: {problem.id})": problem.id for problem in problems
        }

        selected_problem = st.selectbox(
            "Select a problem",
            options=list(problem_options),
            key="schedule_problem",
        )

        delay_days = st.number_input(
            "First review in how many days?",
            min_value=0,
            max_value=365,
            value=1,
            key="problem_delay",
        )

        if st.button("Schedule problem review"):
            try:
                create_review(
                    problem_id=problem_options[selected_problem],
                    due_at=datetime.now(UTC) + timedelta(days=delay_days),
                )
                st.success("Problem review scheduled.")
                st.rerun()
            except (ValueError, SQLAlchemyError) as exc:
                st.error(f"Could not schedule review: {exc}")

else:
    try:
        topics = list_topics_with_notes()
    except SQLAlchemyError:
        st.error("Could not load topics.")
        st.stop()

    if not topics:
        st.info("Create a topic in Topic Knowledge Base first.")
    else:
        topic_options = {
            f"{name} (ID: {topic_id})": topic_id for topic_id, name, _ in topics
        }

        selected_topic = st.selectbox(
            "Select a topic",
            options=list(topic_options),
            key="schedule_topic",
        )

        delay_days = st.number_input(
            "First review in how many days?",
            min_value=0,
            max_value=365,
            value=1,
            key="topic_delay",
        )

        if st.button("Schedule topic review"):
            try:
                create_review(
                    topic_id=topic_options[selected_topic],
                    due_at=datetime.now(UTC) + timedelta(days=delay_days),
                )
                st.success("Topic review scheduled.")
                st.rerun()
            except (ValueError, SQLAlchemyError) as exc:
                st.error(f"Could not schedule review: {exc}")

# -------------------- Upcoming reviews --------------------

st.divider()
st.subheader("Coming up in the next 7 days")

if not upcoming_reviews:
    st.caption("No upcoming reviews scheduled.")
else:
    for review in upcoming_reviews:
        title, item_type = describe_review(review)
        st.write(f"**{title}** · {item_type} · {review.due_at:%d %b %Y, %H:%M UTC}")
