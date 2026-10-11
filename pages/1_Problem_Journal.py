import streamlit as st
from rapidfuzz import fuzz
from sqlalchemy.exc import SQLAlchemyError

from recallcode.problem_service import (
    create_problem,
    list_problems,
    record_attempt,
    update_problem,
)
from recallcode.topic_service import create_topic, list_topics


def rank_problems(problems, query: str, threshold: int = 45):
    """Rank problems by similarity to titles, notes, and topic names."""
    query = query.strip()

    if not query:
        return problems

    ranked = []

    for problem in problems:
        # Title matching handles reordered words and approximate phrases.
        title_score = max(
            fuzz.WRatio(query, problem.title),
            fuzz.token_sort_ratio(query, problem.title),
        )

        # Search the knowledge captured in the problem journal.
        notes = " ".join(
            text
            for text in (
                problem.approach,
                problem.key_observation,
                problem.mistakes,
            )
            if text
        )

        notes_score = fuzz.WRatio(query, notes) if notes else 0

        # Search all topics associated with the problem.
        topic_text = " ".join(topic.name for topic in problem.topics)

        topic_score = fuzz.WRatio(query, topic_text) if topic_text else 0

        # Give titles priority over notes and topics.
        score = max(
            title_score,
            notes_score * 0.85,
            topic_score * 0.80,
        )

        if score >= threshold:
            ranked.append((score, problem))

    ranked.sort(key=lambda item: item[0], reverse=True)

    return [problem for _, problem in ranked]


st.set_page_config(
    page_title="Problem Journal | RecallCode",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Problem Journal")
st.caption("Record problems, preserve insights, and learn from every attempt.")

# Sidebar: topic management
with st.sidebar:
    st.header("Manage Topics")

    with st.form("create_topic_form", clear_on_submit=True):
        topic_name = st.text_input("New topic name")
        topic_description = st.text_area("Description (optional)")
        create_topic_button = st.form_submit_button("Add Topic")

        if create_topic_button:
            try:
                create_topic(topic_name, topic_description)
                st.success(f"Topic '{topic_name.strip()}' created.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except SQLAlchemyError:
                st.error("Could not create the topic. Check the database.")

topics = list_topics()
topic_names = {name: topic_id for topic_id, name in topics}
topic_options = list(topic_names)

tab_add, tab_browse, tab_attempt = st.tabs(
    ["➕ Add Problem", "🔎 Browse Problems", "📝 Record Attempt"]
)

# Add a problem
with tab_add:
    st.subheader("Add a DSA Problem")

    with st.form("add_problem_form", clear_on_submit=True):
        title = st.text_input("Problem title *")
        url = st.text_input("Problem URL")

        col1, col2 = st.columns(2)

        with col1:
            platform = st.selectbox(
                "Platform",
                ["LeetCode", "Codeforces", "Other"],
            )

        with col2:
            difficulty = st.selectbox(
                "Difficulty",
                ["Easy", "Medium", "Hard", "Unrated"],
            )

        selected_topics = st.multiselect(
            "Topics",
            options=topic_options,
            help="Choose all topics that apply to this problem.",
            placeholder="Select one or more topics",
        )

        if not topic_options:
            st.caption(
                "Create topics in the sidebar, or save this problem uncategorized."
            )

        approach = st.text_area("Approach")
        observation = st.text_area("Key observation")
        mistakes = st.text_area("Mistakes / lessons learned")

        time_complexity = st.text_input(
            "Time complexity",
            placeholder="O(n)",
        )
        space_complexity = st.text_input(
            "Space complexity",
            placeholder="O(1)",
        )

        submitted = st.form_submit_button("Save Problem", type="primary")

        if submitted:
            if not title.strip():
                st.error("Problem title is required.")
            else:
                try:
                    problem_id = create_problem(
                        title=title,
                        platform=platform,
                        url=url.strip() or None,
                        difficulty=(None if difficulty == "Unrated" else difficulty),
                        topic_ids=[topic_names[name] for name in selected_topics],
                    )

                    update_problem(
                        problem_id,
                        approach=approach.strip() or None,
                        key_observation=observation.strip() or None,
                        mistakes=mistakes.strip() or None,
                        time_complexity=time_complexity.strip() or None,
                        space_complexity=space_complexity.strip() or None,
                    )

                    st.success(f"Saved '{title.strip()}' (ID: {problem_id}).")
                    st.rerun()

                except ValueError as exc:
                    st.error(str(exc))
                except SQLAlchemyError:
                    st.error("Could not save the problem. Check the database.")

# Browse and search problems
with tab_browse:
    st.subheader("Your Problems")

    search = st.text_input(
        "Search problems",
        placeholder="Try 'sort color' or 'Dutch National Flag'",
        help=(
            "Uses fuzzy text similarity across problem titles, notes, and topic names."
        ),
    )

    col1, col2 = st.columns(2)

    with col1:
        platform_filter = st.selectbox(
            "Filter by platform",
            ["All", "LeetCode", "Codeforces", "Other"],
        )

    with col2:
        topic_filter = st.selectbox(
            "Filter by topic",
            ["All"] + topic_options,
        )

    try:
        # Fetch the full filtered candidate set first.
        # Do not use list_problems(search=search) here: ordinary
        # database search could exclude fuzzy matches before ranking.
        problems = list_problems(
            platform=(None if platform_filter == "All" else platform_filter),
            topic_id=topic_names.get(topic_filter),
        )

        problems = rank_problems(problems, search)

        if not problems:
            st.info(
                "No matching problems found. Try different keywords "
                "or add more details to your problem notes."
            )
        else:
            st.caption(f"{len(problems)} problem(s) found.")

            for problem in problems:
                problem_topics = (
                    ", ".join(topic.name for topic in problem.topics) or "Uncategorized"
                )

                with st.expander(f"#{problem.id} · {problem.title} — {problem_topics}"):
                    st.write(
                        f"**Platform:** {problem.platform}  \n"
                        f"**Difficulty:** {problem.difficulty or 'Not set'}  \n"
                        f"**Status:** {problem.status}"
                    )

                    if problem.url:
                        st.markdown(f"[Open problem]({problem.url})")

                    if problem.approach:
                        st.markdown("**Approach**")
                        st.write(problem.approach)

                    if problem.key_observation:
                        st.markdown("**Key observation**")
                        st.write(problem.key_observation)

                    if problem.mistakes:
                        st.markdown("**Mistakes / lessons**")
                        st.write(problem.mistakes)

                    st.markdown(
                        f"**Complexity:** Time "
                        f"`{problem.time_complexity or '—'}` "
                        f"| Space `{problem.space_complexity or '—'}`"
                    )

                    statuses = ["attempted", "solved", "needs_revision"]

                    new_status = st.selectbox(
                        "Update status",
                        statuses,
                        index=(
                            statuses.index(problem.status)
                            if problem.status in statuses
                            else 0
                        ),
                        key=f"status_{problem.id}",
                    )

                    if st.button(
                        "Save status",
                        key=f"save_status_{problem.id}",
                    ):
                        try:
                            updated = update_problem(
                                problem.id,
                                status=new_status,
                            )

                            if updated:
                                st.success("Status updated.")
                                st.rerun()
                            else:
                                st.error("Problem not found.")
                        except (ValueError, SQLAlchemyError):
                            st.error("Could not update the problem status.")

    except SQLAlchemyError:
        st.error("Could not load problems. Check the database.")

# Record a new attempt
with tab_attempt:
    st.subheader("Record an Attempt")

    try:
        all_problems = list_problems()

        if not all_problems:
            st.info("Add a problem before recording an attempt.")
        else:
            problem_options = {
                f"#{problem.id} — {problem.title}": problem.id
                for problem in all_problems
            }

            with st.form("record_attempt_form", clear_on_submit=True):
                selected_problem = st.selectbox(
                    "Problem",
                    list(problem_options),
                )

                outcome = st.selectbox(
                    "Outcome",
                    [
                        "solved_independently",
                        "needed_hint",
                        "could_not_solve",
                        "reviewed_solution",
                    ],
                )

                used_hint = st.checkbox("Used a hint")

                minutes = st.number_input(
                    "Time taken (minutes)",
                    min_value=0,
                    value=0,
                    step=5,
                )

                attempt_notes = st.text_area("What did you learn from this attempt?")

                attempt_submitted = st.form_submit_button(
                    "Save Attempt",
                    type="primary",
                )

                if attempt_submitted:
                    try:
                        attempt_id = record_attempt(
                            problem_id=problem_options[selected_problem],
                            outcome=outcome,
                            used_hint=used_hint,
                            time_taken_minutes=minutes,
                            notes=attempt_notes.strip() or None,
                        )

                        st.success(f"Attempt recorded (ID: {attempt_id}).")
                    except ValueError as exc:
                        st.error(str(exc))
                    except SQLAlchemyError:
                        st.error("Could not record the attempt.")

    except SQLAlchemyError:
        st.error("Could not load problems. Check the database.")
