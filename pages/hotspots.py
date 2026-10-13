"""
Hotspots Page - Codebase Evolution Intelligence System.
Displays multi-factor Code Hotspot scores based on File Change Frequency,
Radon Code Complexity, and Heuristic Bug-Fix activity.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from analysis import get_hotspots_df, get_repository_summary
from chart_theme import apply_chart_theme


def render_hotspots():
    repo_id = st.session_state.get("selected_repo_id")
    if not repo_id:
        st.info("👈 Please select or analyze a GitHub repository from the sidebar to view hotspot analytics.")
        return

    summary = get_repository_summary(repo_id)
    hotspots_df = get_hotspots_df(repo_id)

    st.title("🔥 Code Hotspot Analysis")
    st.caption(f"Repository: **{summary.get('name', 'N/A')}** | Identifying high-maintenance & risk-prone files")
    st.markdown("---")

    if hotspots_df.empty:
        st.info("No hotspot data calculated yet.")
        return

    # Explanatory Callout Banner
    st.info(
        "🧠 **How Hotspots are Calculated:**\n\n"
        "A file is identified as a hotspot based on three weighted factors:\n"
        "- **Change Frequency (40%):** How often developers touch or refactor the file.\n"
        "- **Bug-Fix Activity (35%):** Number of commits touching this file that match bug-fix keywords (`fix`, `bug`, `issue`, etc. - heuristic).\n"
        "- **Code Complexity (25%):** Radon Cyclomatic Complexity score and grade (A to F).\n\n"
        "Files with scores **≥ 65** are classified as **High Risk**, scores **35 - 64** as **Medium Risk**, and **< 35** as **Low Risk / Stable**."
    )

    # Risk Metrics
    high_risk_count = (hotspots_df["Risk Level"] == "High").sum()
    med_risk_count = (hotspots_df["Risk Level"] == "Medium").sum()
    low_risk_count = (hotspots_df["Risk Level"] == "Low").sum()

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Analyzed Files", f"{len(hotspots_df):,}")
    with col_m2:
        st.metric("🚨 High Risk Hotspots", f"{high_risk_count:,}")
    with col_m3:
        st.metric("⚠️ Medium Risk Hotspots", f"{med_risk_count:,}")
    with col_m4:
        st.metric("✅ Stable / Low Risk", f"{low_risk_count:,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Hotspot Visual Matrix
    st.subheader("🎯 Hotspot Matrix: Churn vs Complexity vs Bug Fixes")
    bubble_fig = px.scatter(
        hotspots_df,
        x="Commits",
        y="Complexity (CC)",
        size="Bug Fixes",
        color="Hotspot Score",
        color_continuous_scale=[[0, "#38bdf8"], [0.35, "#fbbf24"], [0.65, "#f97316"], [1.0, "#dc2626"]],
        hover_name="File Path",
        hover_data=["Risk Level", "LOC", "Commits", "Bug Fixes", "Complexity (CC)"],
        labels={"Commits": "File Change Frequency (Commits)", "Complexity (CC)": "Radon Cyclomatic Complexity"}
    )
    bubble_fig.update_traces(
        marker=dict(line=dict(width=1.5, color="#0f172a"))
    )
    bubble_fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(text="Hotspot Score", font=dict(color="#0f172a", size=12)),
            tickfont=dict(color="#0f172a", size=11),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cbd5e1",
            borderwidth=1
        )
    )
    apply_chart_theme(bubble_fig, height=390, show_legend=False)
    st.plotly_chart(bubble_fig, use_container_width=True)

    st.markdown("---")

    # Hotspots Ranked Table
    st.subheader("📋 Ranked Code Hotspots")
    
    # Filter by risk level
    risk_filter = st.radio("Filter by Risk Level:", ["All Files", "High Risk Only", "Medium & High Risk"], horizontal=True)
    display_df = hotspots_df.copy()
    if risk_filter == "High Risk Only":
        display_df = display_df[display_df["Risk Level"] == "High"]
    elif risk_filter == "Medium & High Risk":
        display_df = display_df[display_df["Risk Level"].isin(["High", "Medium"])]

    st.dataframe(
        display_df[[
            "File Path", "Hotspot Score", "Risk Level", "Commits",
            "Bug Fixes", "Complexity (CC)", "Complexity Rank", "LOC", "Reason / Heuristic"
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Hotspot Score": st.column_config.ProgressColumn(
                "Hotspot Score",
                format="%.1f",
                min_value=0,
                max_value=100
            ),
            "Complexity (CC)": st.column_config.NumberColumn("Complexity (CC)", format="%.2f"),
        }
    )

    # Deep-dive file inspector
    st.markdown("---")
    st.subheader("🔍 Hotspot Deep Dive & Explanation")
    selected_file = st.selectbox(
        "Select a hotspot file to view root-cause explanation:",
        options=display_df["File Path"].tolist()[:50] if not display_df.empty else []
    )

    if selected_file:
        row = display_df[display_df["File Path"] == selected_file].iloc[0]
        st.markdown(f"#### `{selected_file}`")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Hotspot Score", f"{row['Hotspot Score']:.1f} / 100")
        c2.metric("Commit Modifications", f"{row['Commits']} times")
        c3.metric("Bug Fix Involvements", f"{row['Bug Fixes']} times")
        c4.metric("Radon Complexity", f"{row['Complexity (CC)']} (Rank {row['Complexity Rank']})")

        st.markdown(f"**Why this file is flagged:**")
        st.markdown(f"> *{row['Reason / Heuristic']}*")

        st.markdown("**Engineering Recommendation:**")
        if row["Risk Level"] == "High":
            st.error("🚨 **High Refactoring Priority:** This file undergoes frequent modifications and bug fixes while maintaining high cyclomatic complexity. Consider breaking it down into smaller, cohesive modules and adding unit test coverage.")
        elif row["Risk Level"] == "Medium":
            st.warning("⚠️ **Moderate Attention:** This file shows significant churn or moderate complexity. Monitor changes closely during code reviews.")
        else:
            st.success("✅ **Stable:** This file demonstrates low churn and manageable complexity.")


render_hotspots()
