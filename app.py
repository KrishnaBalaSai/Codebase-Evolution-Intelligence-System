"""
Codebase Evolution Intelligence System - Main Streamlit Application.
Provides repository ingestion, analysis progress tracking, database management,
and multi-page dashboard navigation.
"""

import os
import streamlit as st
from database import test_connection, init_db
from analysis import (
    get_repositories,
    run_repository_analysis,
    delete_repository
)

# Page configuration
st.set_page_config(
    page_title="Codebase Evolution Intelligence System",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database Schema if not already present
try:
    init_db()
except Exception as e:
    st.error(f"Failed to initialize database: {e}")

# Sidebar Header & Branding
with st.sidebar:
    st.title("🧬 Codebase Evolution")
    st.caption("Git Repository Evolution & Intelligence System")
    st.markdown("---")

    # Live Database Connection Check
    db_ok, db_msg = test_connection()
    if db_ok:
        st.success("🟢 MySQL Connected", icon="✅")
    else:
        st.error("🔴 MySQL Disconnected", icon="❌")
        st.caption(f"Error: {db_msg}")
        st.info("Check your `.env` configuration for MySQL host, port, user, and password.")

    st.markdown("---")

    # Repository Ingestion Form
    st.subheader("📥 Analyze Repository")
    repo_url_input = st.text_input(
        "Public GitHub URL",
        placeholder="https://github.com/owner/repository",
        help="Enter any public Git or GitHub repository URL to clone and analyze."
    )

    # Preset examples for fast testing
    st.caption("Quick test presets:")
    col_pre1, col_pre2 = st.columns(2)
    with col_pre1:
        if st.button("psf/requests", use_container_width=True):
            repo_url_input = "https://github.com/psf/requests"
    with col_pre2:
        if st.button("pallets/flask", use_container_width=True):
            repo_url_input = "https://github.com/pallets/flask"

    analyze_clicked = st.button("🚀 Analyze Repository", type="primary", use_container_width=True)

    if analyze_clicked:
        if not repo_url_input or not repo_url_input.strip():
            st.error("Please enter a valid GitHub repository URL.")
        elif not db_ok:
            st.error("Cannot analyze: MySQL connection is not available. Please verify MySQL service.")
        else:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def progress_callback(fraction: float, message: str):
                clamped = max(0.0, min(1.0, fraction))
                progress_bar.progress(clamped)
                status_text.text(f"⏳ {message}")

            try:
                status_text.text("Starting clone and analysis pipeline...")
                new_repo_id = run_repository_analysis(repo_url_input.strip(), progress_callback)
                st.session_state["selected_repo_id"] = new_repo_id
                progress_bar.progress(1.0)
                status_text.text("✅ Analysis complete!")
                st.success("Repository analyzed and saved to MySQL successfully!")
                st.rerun()
            except Exception as ex:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Analysis failed: {str(ex)}")

    st.markdown("---")

    # Existing Repositories Selector
    st.subheader("📁 Analyzed Repositories")
    existing_repos = get_repositories()

    if existing_repos:
        repo_options = {r["id"]: f"{r['name']} ({r['total_commits']} commits)" for r in existing_repos}
        repo_ids = list(repo_options.keys())

        # Determine default selection
        current_id = st.session_state.get("selected_repo_id")
        current_index = repo_ids.index(current_id) if current_id in repo_ids else 0

        selected_id = st.selectbox(
            "Select Repository:",
            options=repo_ids,
            format_func=lambda x: repo_options[x],
            index=current_index,
            key="repo_selector"
        )
        st.session_state["selected_repo_id"] = selected_id

        # Delete Repository Option
        with st.expander("⚙️ Repository Settings"):
            if st.button("🗑️ Delete Selected Repository", use_container_width=True):
                delete_repository(selected_id)
                st.session_state.pop("selected_repo_id", None)
                st.warning("Repository deleted from database.")
                st.rerun()
    else:
        st.info("No repositories analyzed yet. Enter a GitHub URL above to get started!")

    st.markdown("---")
    st.caption("Built with Python, MySQL, Streamlit, GitPython, Pandas, Plotly & Radon.")


# Multi-Page Navigation definition
pages = [
    st.Page("pages/overview.py", title="Overview", icon="📊", default=True),
    st.Page("pages/commits.py", title="Commits", icon="📜"),
    st.Page("pages/files.py", title="Files", icon="📁"),
    st.Page("pages/hotspots.py", title="Hotspots", icon="🔥"),
    st.Page("pages/contributors.py", title="Contributors", icon="👥"),
    st.Page("pages/evolution.py", title="Evolution", icon="📈"),
]

# Run selected page
pg = st.navigation(pages)
pg.run()
