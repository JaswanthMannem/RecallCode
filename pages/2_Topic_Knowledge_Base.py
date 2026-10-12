import streamlit as st
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from recallcode.note_service import read_topic_notes, save_topic_notes
from recallcode.problem_service import list_problems
from recallcode.topic_service import create_topic, list_topics_with_notes

st.set_page_config(
    page_title="Topic Knowledge Base | RecallCode",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Topic Knowledge Base")
st.caption("Build your DSA knowledge one topic at a time.")

# -------------------- Create a topic --------------------

with st.expander("➕ Create a new topic"):
    with st.form("create_topic_form", clear_on_submit=True):
        topic_name = st.text_input(
            "Topic name",
            placeholder="e.g., Sliding Window",
        )
        topic_description = st.text_input(
            "Description",
            placeholder="e.g., Techniques for processing contiguous ranges",
        )
        create_submitted = st.form_submit_button("Create topic")

    if create_submitted:
        try:
            topic_id = create_topic(
                name=topic_name,
                description=topic_description,
            )
            st.success(f"Topic created successfully (ID: {topic_id}).")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except IntegrityError:
            st.error("A topic with that name already exists.")
        except SQLAlchemyError:
            st.error("Database error while creating the topic.")

# -------------------- Load topics --------------------

try:
    topics = list_topics_with_notes()
except SQLAlchemyError:
    st.error("Could not load topics from the database.")
    st.stop()

if not topics:
    st.info("No topics yet. Create your first topic above to get started.")
    st.stop()

topic_options = {f"{name} (ID: {topic_id})": topic_id for topic_id, name, _ in topics}

selected_label = st.selectbox(
    "Choose a topic",
    options=list(topic_options),
)
selected_topic_id = topic_options[selected_label]

selected_topic = next(topic for topic in topics if topic[0] == selected_topic_id)
_, selected_topic_name, selected_description = selected_topic

if selected_description:
    st.caption(selected_description)

# -------------------- Load notes --------------------

editor_key = f"topic_notes_{selected_topic_id}"

if editor_key not in st.session_state:
    try:
        st.session_state[editor_key] = read_topic_notes(selected_topic_id)
    except (ValueError, OSError, SQLAlchemyError) as exc:
        st.error(f"Could not load notes: {exc}")
        st.stop()

st.subheader(f"Notes: {selected_topic_name}")

editor_column, preview_column = st.columns(2, gap="large")

with editor_column:
    st.markdown("#### Markdown editor")
    st.caption("Use headings, bullet points, code blocks, and tables.")

    edited_notes = st.text_area(
        "Topic notes",
        key=editor_key,
        height=480,
        label_visibility="collapsed",
        placeholder="""# Sliding Window

## Core idea

Explain the technique in your own words.

## When to use it

- Recognition patterns
- Constraints that suggest this technique

## Common patterns

## Python template

```python
# Add your reusable template here
```

## Complexity

- Time:
- Space:

## Common mistakes

## Related problems
""",
    )

    if st.button("💾 Save notes", type="primary"):
        try:
            save_topic_notes(selected_topic_id, edited_notes)
            st.success("Notes saved successfully.")
        except (ValueError, TypeError, OSError, SQLAlchemyError) as exc:
            st.error(f"Could not save notes: {exc}")

with preview_column:
    st.markdown("#### Live preview")

    with st.container(height=480, border=True):
        if edited_notes.strip():
            st.markdown(edited_notes)
        else:
            st.caption("Your Markdown preview will appear here.")

# -------------------- Related problems --------------------

st.divider()
st.subheader(f"Problems linked to {selected_topic_name}")

try:
    problems = list_problems(topic_id=selected_topic_id)
except SQLAlchemyError:
    st.error("Could not load problems for this topic.")
    st.stop()

if not problems:
    st.info(
        "No problems are linked to this topic yet. "
        "Open Problem Journal and assign this topic to a problem."
    )
else:
    st.caption(f"{len(problems)} linked problem(s)")

    for problem in problems:
        with st.container(border=True):
            header_col, status_col = st.columns([4, 1])

            with header_col:
                st.markdown(f"**{problem.title}**")

                metadata = [
                    value for value in (problem.platform, problem.difficulty) if value
                ]
                st.caption(" · ".join(metadata))

            with status_col:
                st.write(problem.status.replace("_", " ").title())

            if problem.url:
                st.markdown(f"[Open problem]({problem.url})")

            if problem.key_observation:
                st.markdown("**Key observation**")
                st.write(problem.key_observation)

            if problem.approach:
                with st.expander("Review approach"):
                    st.write(problem.approach)

            if problem.mistakes:
                with st.expander("Review mistakes"):
                    st.write(problem.mistakes)

            if problem.time_complexity or problem.space_complexity:
                st.caption(
                    f"Time: {problem.time_complexity or 'Not recorded'}"
                    f" | Space: {problem.space_complexity or 'Not recorded'}"
                )

st.divider()
st.caption(
    "Topic notes are stored as Markdown files and can be version-controlled with Git."
)
