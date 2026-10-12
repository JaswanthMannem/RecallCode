import pandas as pd
import streamlit as st

from recallcode.dashboard_service import (
    get_dashboard_summary,
    get_recent_attempts,
    get_topic_progress,
)

st.set_page_config(
    page_title="Progress Dashboard | RecallCode",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Progress Dashboard")
st.caption("Track your DSA practice, topic progress, and revision workload.")

if st.button("🔄 Refresh Dashboard"):
    st.rerun()

summary = get_dashboard_summary()
topic_progress = get_topic_progress()
recent_attempts = get_recent_attempts(limit=10)

# --- Overview metrics ---
st.subheader("Your Practice Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Problems Tracked", summary["total_problems"])
col2.metric("Total Attempts", summary["total_attempts"])
col3.metric("Reviews Due", summary["due_reviews"])
col4.metric("Overdue Reviews", summary["overdue_reviews"])

st.divider()

# --- Problem breakdowns ---
left, right = st.columns(2)

with left:
    st.subheader("Problems by Status")

    status_counts = summary["status_counts"]

    if status_counts:
        status_df = pd.DataFrame(
            {
                "Status": list(status_counts.keys()),
                "Count": list(status_counts.values()),
            }
        ).set_index("Status")

        st.bar_chart(status_df)
    else:
        st.info(
            "No problems tracked yet. Add your first problem in the Problem Journal."
        )

with right:
    st.subheader("Problems by Difficulty")

    difficulty_counts = summary["difficulty_counts"]

    if difficulty_counts:
        difficulty_df = pd.DataFrame(
            {
                "Difficulty": list(difficulty_counts.keys()),
                "Count": list(difficulty_counts.values()),
            }
        ).set_index("Difficulty")

        st.bar_chart(difficulty_df)
    else:
        st.info("Difficulty statistics will appear when you add problems.")

st.divider()

# --- Topic progress ---
st.subheader("Topic-wise Progress")

if topic_progress:
    topic_df = pd.DataFrame(topic_progress)

    display_df = topic_df[
        [
            "topic",
            "total_problems",
            "solved_problems",
            "completion_percent",
        ]
    ].rename(
        columns={
            "topic": "Topic",
            "total_problems": "Problems Tracked",
            "solved_problems": "Solved",
            "completion_percent": "Completion (%)",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    chart_df = display_df.set_index("Topic")[["Completion (%)"]]
    st.bar_chart(chart_df, y="Completion (%)")
else:
    st.info(
        "Create topics and associate problems with them to see topic-wise progress."
    )

st.divider()

# --- Recent attempts ---
st.subheader("Recent Attempts")

if recent_attempts:
    attempts_data = [
        {
            "Problem": attempt.problem.title,
            "Outcome": attempt.outcome,
            "Attempted At": attempt.attempted_at.strftime("%d %b %Y, %I:%M %p"),
            "Time (min)": attempt.time_taken_minutes,
            "Used Hint": "Yes" if attempt.used_hint else "No",
        }
        for attempt in recent_attempts
    ]

    st.dataframe(
        pd.DataFrame(attempts_data),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Your recorded problem attempts will appear here.")

st.divider()

# --- Revision history summary ---
st.subheader("Revision Summary")

review_col1, review_col2 = st.columns(2)

review_col1.metric("Total Reviews Created", summary["total_reviews"])
review_col2.metric("Reviews Completed", summary["completed_reviews"])
