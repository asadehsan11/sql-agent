"""Streamlit UI for the SQL agent."""
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from src.service import ask_and_log
from src.sql_agent import run_query

REPO_URL = "https://github.com/asadehsan11/sql-agent"
EXAMPLES = [
    "Which 5 artists have the most albums?",
    "What was the total sales amount per country? Show the top 3.",
    "Which genre has the most tracks?",
    "Who are the 5 customers who spent the most?",
]

st.set_page_config(page_title="SQL Agent", page_icon="🗄️", layout="wide")

CSS = (Path(__file__).parent / "assets" / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def count(table):
    return run_query(f"SELECT COUNT(*) FROM {table}")[1][0][0]


tables = [
    r[0]
    for r in run_query(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )[1]
]
n_tracks = count("Track")
n_customers = count("Customer")
n_invoices = count("Invoice")

st.markdown(
    f"""
    <div class="navbar">
        <div class="brand">🗄️ SQL AGENT</div>
        <a href="{REPO_URL}" target="_blank">GitHub</a>
    </div>
    <div class="hero">
        <h1>Ask your database <span class="accent">anything</span></h1>
        <p>Type a question in plain English. The agent writes the SQL, runs it
        read-only, and explains the result. You can always see the query it used.</p>
        <span class="pill p-cyan">Plain English</span>
        <span class="pill p-pink">Read-only SQL</span>
        <span class="pill p-green">Transparent</span>
    </div>
    <div class="tiles">
        <div class="tile"><div class="tile-label">Tracks</div><div class="tile-num n-blue">{n_tracks:,}</div></div>
        <div class="tile"><div class="tile-label">Customers</div><div class="tile-num n-pink">{n_customers:,}</div></div>
        <div class="tile"><div class="tile-label">Invoices</div><div class="tile-num n-green">{n_invoices:,}</div></div>
        <div class="tile"><div class="tile-label">Tables</div><div class="tile-num n-cyan">{len(tables)}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []

left, right = st.columns([1, 2], gap="large")

with left:
    with st.container(border=True):
        st.markdown('<div class="card-title">About the data</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="note">Chinook: a sample database of a digital music store '
            "with artists, albums, tracks, customers and invoices.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="margin-top:.7rem">'
            + "".join(f'<span class="chip">{html.escape(t)}</span>' for t in tables)
            + "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="card-title" style="margin-top:1rem">Try an example</div>',
            unsafe_allow_html=True,
        )
        for i, example in enumerate(EXAMPLES):
            if st.button(example, key=f"ex{i}", use_container_width=True):
                st.session_state.pending = example

with right:
    with st.container(border=True):
        st.markdown('<div class="card-title">Ask a question</div>', unsafe_allow_html=True)
        with st.form("ask_form", clear_on_submit=True):
            typed = st.text_input(
                "Your question",
                placeholder="e.g. Which genre sells the most?",
                label_visibility="collapsed",
            )
            asked = st.form_submit_button("Ask")

    question = st.session_state.pop("pending", None) or (typed.strip() if asked else None)
    if question:
        with st.spinner("Writing the SQL and running it..."):
            result = ask_and_log(question)
        st.session_state.history.append(result)

    if st.session_state.history:
        latest = st.session_state.history[-1]
        st.markdown(
            f'<div class="card-title" style="margin-top:1rem">Question</div>'
            f'<div style="font-size:1.2rem;font-weight:700">{html.escape(latest["question"])}</div>',
            unsafe_allow_html=True,
        )
        if latest["error"]:
            st.error("Sorry, I couldn't answer that. Try rephrasing the question.")
            with st.expander("Details"):
                st.code(latest["error"])
        else:
            with st.container(border=True):
                st.markdown('<div class="card-title">Answer</div>', unsafe_allow_html=True)
                st.markdown(latest["answer"].replace("$", "\\$"))
            st.markdown(
                '<div class="card-title" style="margin-top:1rem">SQL used</div>',
                unsafe_allow_html=True,
            )
            st.code(latest["sql"], language="sql")
            n = len(latest["rows"])
            st.markdown(
                f'<div class="card-title" style="margin-top:1rem">Result ({n} rows)</div>',
                unsafe_allow_html=True,
            )
            st.dataframe(
                pd.DataFrame(latest["rows"], columns=latest["columns"]),
                use_container_width=True,
                hide_index=True,
            )
            if n >= 100:
                st.caption("Showing the first 100 rows.")
        older = st.session_state.history[:-1]
        if older:
            with st.expander(f"Earlier questions ({len(older)})"):
                for item in reversed(older):
                    st.markdown(f"**Q:** {item['question']}")
                    st.markdown((item["answer"] or "No answer.").replace("$", "\\$"))
                    st.divider()
    else:
        with st.container(border=True):
            st.markdown(
                "Your answer will appear here. Pick an example on the left "
                "or type your own question."
            )

st.markdown(
    f'<div class="footer">Built by Asad Ehsan · Data: Chinook sample database · '
    f'<a href="{REPO_URL}" target="_blank">View source on GitHub</a></div>',
    unsafe_allow_html=True,
)