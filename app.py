import streamlit as st

from recallcode.dashboard_service import (
    get_dashboard_summary,
    get_topic_progress,
)
from recallcode.revision_service import list_due_reviews

st.set_page_config(
    page_title="RecallCode",
    page_icon="🧠",
    layout="wide",
)

# --- Header ---
st.title("🧠 RecallCode")
st.subheader("Your personal DSA knowledge system")
st.markdown("Learn patterns. Record insights. Retain knowledge.")

st.divider()

# --- Fetch live data ---
summary = get_dashboard_summary()
topics = get_topic_progress()
due_reviews = list_due_reviews()

solved_problems = summary["status_counts"].get("solved", 0)

topics_covered = sum(1 for topic in topics if topic["total_problems"] > 0)

weak_topics = sum(
    1
    for topic in topics
    if topic["total_problems"] > 0 and topic["completion_percent"] < 50
)

# --- Overview metrics ---
st.header("Your Progress")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Problems Solved", solved_problems)
col2.metric("Topics Practiced", topics_covered)
col3.metric("Reviews Due", len(due_reviews))
col4.metric("Weak Topics", weak_topics)

st.divider()

# --- Quick navigation ---
st.header("Your Workspace")
st.write("Pick up where you left off.")

nav1, nav2 = st.columns(2)

with nav1:
    st.subheader("📝 Problem Journal")
    st.write("Record solutions, approaches, mistakes, and complexity.")
    st.page_link(
        "pages/1_Problem_Journal.py",
        label="Open Problem Journal",
        icon="📝",
    )

    st.subheader("📚 Topic Knowledge Base")
    st.write("Organize topic notes and connect them to problems.")
    st.page_link(
        "pages/2_Topic_Knowledge_Base.py",
        label="Open Topic Knowledge Base",
        icon="📚",
    )

with nav2:
    st.subheader("🔁 Revision Queue")
    st.write("Review problems and concepts due for revision.")
    st.page_link(
        "pages/3_Revision_Queue.py",
        label="Open Revision Queue",
        icon="🔁",
    )

    st.subheader("📊 Progress Dashboard")
    st.write("Explore your problem statistics and topic progress.")
    st.page_link(
        "pages/4_Progress_Dashboard.py",
        label="Open Progress Dashboard",
        icon="📊",
    )

st.divider()

# --- Revision reminders ---
st.header("📌 Revision Reminders")

if due_reviews:
    st.warning(
        f"You have {len(due_reviews)} review(s) waiting. "
        "Open the Revision Queue to work through them."
    )
    st.page_link(
        "pages/3_Revision_Queue.py",
        label="Review Now",
        icon="🔁",
    )
else:
    st.success("You're all caught up! No reviews are currently due.")

st.caption("RecallCode — build your DSA knowledge one problem at a time.")
