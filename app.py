import streamlit as st

st.set_page_config(
    page_title="RecallCode",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 RecallCode")
st.subheader("Your personal DSA knowledge system")

st.markdown("Learn patterns. Record insights. Retain knowledge.")

st.divider()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Problems Solved", 0)
col2.metric("Topics Covered", 0)
col3.metric("Reviews Due", 0)
col4.metric("Weak Topics", 0)

st.divider()

st.header("Welcome to RecallCode")
st.write(
    "Your journey to mastering DSA starts here. "
    "Soon, you will be able to track problems, "
    "organize topic notes, and revise concepts."
)
