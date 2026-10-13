"""
Analysis orchestration and database persistence pipeline.
Coordinates Git extraction, Radon metrics computation, hotspot scoring,
and querying for Streamlit dashboard views.
"""

import os
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from database import get_session, get_db_context, init_db
from models import Repository, Developer, Commit, File, CommitFile, FileMetric
from git_analyzer import (
    parse_github_url,
    get_repo_clone_path,
    clone_or_open_repository,
    extract_git_history
)
from metrics import analyze_file_complexity, calculate_hotspot_scores


def run_repository_analysis(
    repo_url: str,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> int:
    """
    Orchestrates full repository analysis and saves data into MySQL.
    Returns the analyzed repository ID.
    """
    # 1. Validate URL
    is_valid, norm_url, repo_name = parse_github_url(repo_url)
    if not is_valid:
        raise ValueError(repo_name)

    if progress_callback:
        progress_callback(0.05, f"Starting analysis for {repo_name}...")

    # Ensure DB tables are initialized
    init_db()

    # 2. Clone or open repository
    clone_dir = get_repo_clone_path(norm_url)
    repo = clone_or_open_repository(norm_url, clone_dir, progress_callback)

    # 3. Extract Git commit history and file tracking
    if progress_callback:
        progress_callback(0.20, "Extracting Git commits and file history...")
    git_data = extract_git_history(repo, max_commits=2500, progress_callback=progress_callback)

    # 4. Compute Radon metrics for files
    if progress_callback:
        progress_callback(0.80, "Calculating Radon code complexity and raw metrics...")

    files_list = git_data["files"]
    for f in files_list:
        file_full_path = os.path.join(clone_dir, f["file_path"])
        f_metrics = analyze_file_complexity(file_full_path, f["file_path"])
        f.update(f_metrics)

    # 5. Compute Hotspot scores
    if progress_callback:
        progress_callback(0.88, "Calculating multi-factor code hotspot scores...")
    scored_files = calculate_hotspot_scores(files_list)

    # 6. Store in MySQL database
    if progress_callback:
        progress_callback(0.92, "Persisting repository analytics into MySQL database...")

    with get_db_context() as session:
        # Check if repository already exists in DB
        repo_record = session.query(Repository).filter_by(url=norm_url).first()
        if repo_record:
            # Clear old records for this repository to re-populate fresh data
            session.delete(repo_record)
            session.flush()

        # Compute total LOC across active files
        total_loc = sum(f.get("loc", 0) for f in scored_files if f.get("is_active", True))

        # Insert Repository record
        repo_record = Repository(
            name=repo_name,
            url=norm_url,
            default_branch=git_data["default_branch"],
            cloned_path=clone_dir,
            total_commits=git_data["total_commits"],
            total_files=git_data["total_files"],
            total_lines_of_code=total_loc,
            analyzed_at=datetime.utcnow()
        )
        session.add(repo_record)
        session.flush()  # Populates repo_record.id
        repo_id = repo_record.id

        # Insert Developers
        dev_map: Dict[str, int] = {}
        for dev in git_data["developers"]:
            dev_obj = Developer(
                repository_id=repo_id,
                name=dev["name"],
                email=dev["email"],
                total_commits=dev["total_commits"],
                total_lines_added=dev["total_lines_added"],
                total_lines_deleted=dev["total_lines_deleted"],
                first_commit_date=dev["first_commit_date"],
                last_commit_date=dev["last_commit_date"],
            )
            session.add(dev_obj)
            session.flush()
            dev_map[dev["email"]] = dev_obj.id

        # Insert Files and FileMetrics
        file_map: Dict[str, int] = {}
        for f in scored_files:
            file_obj = File(
                repository_id=repo_id,
                file_path=f["file_path"],
                file_name=f["file_name"],
                file_extension=f["file_extension"],
                current_loc=f.get("loc", 0),
                change_count=f["change_count"],
                lines_added=f["lines_added"],
                lines_deleted=f["lines_deleted"],
                bug_fix_count=f["bug_fix_count"],
                is_active=f.get("is_active", True)
            )
            session.add(file_obj)
            session.flush()
            file_map[f["file_path"]] = file_obj.id

            # Insert FileMetric
            metric_obj = FileMetric(
                file_id=file_obj.id,
                loc=f.get("loc", 0),
                sloc=f.get("sloc", 0),
                comments=f.get("comments", 0),
                cyclomatic_complexity=f.get("cyclomatic_complexity", 1.0),
                complexity_rank=f.get("complexity_rank", "A"),
                change_count=f["change_count"],
                bug_fix_count=f["bug_fix_count"],
                hotspot_score=f.get("hotspot_score", 0.0),
                analyzed_at=datetime.utcnow()
            )
            session.add(metric_obj)

        # Insert Commits and CommitFiles
        for c in git_data["commits"]:
            dev_id = dev_map.get(c["author_email"])
            commit_obj = Commit(
                repository_id=repo_id,
                developer_id=dev_id,
                commit_hash=c["commit_hash"],
                author_name=c["author_name"],
                author_email=c["author_email"],
                message=c["message"],
                commit_date=c["commit_date"],
                files_changed=c["files_changed"],
                lines_added=c["lines_added"],
                lines_deleted=c["lines_deleted"],
                is_bug_fix=c["is_bug_fix"]
            )
            session.add(commit_obj)
            session.flush()

            # Insert CommitFiles
            commit_file_objects = []
            for cf in c.get("commit_files", []):
                f_id = file_map.get(cf["file_path"])
                if f_id:
                    commit_file_objects.append(CommitFile(
                        commit_id=commit_obj.id,
                        file_id=f_id,
                        change_type=cf["change_type"],
                        lines_added=cf["lines_added"],
                        lines_deleted=cf["lines_deleted"]
                    ))
            if commit_file_objects:
                session.bulk_save_objects(commit_file_objects)

    if progress_callback:
        progress_callback(1.0, f"Analysis complete for {repo_name}!")

    return repo_id


# ==========================================
# Query Functions for Streamlit Dashboard
# ==========================================

def get_repositories() -> List[Dict[str, Any]]:
    """Returns a list of all analyzed repositories in the database."""
    init_db()
    with get_db_context() as session:
        repos = session.query(Repository).order_by(desc(Repository.analyzed_at)).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "url": r.url,
                "default_branch": r.default_branch,
                "total_commits": r.total_commits,
                "total_files": r.total_files,
                "total_loc": r.total_lines_of_code,
                "analyzed_at": r.analyzed_at
            }
            for r in repos
        ]


def get_repository_summary(repo_id: int) -> Dict[str, Any]:
    """Returns high-level KPI metrics for the repository overview."""
    with get_db_context() as session:
        repo = session.query(Repository).filter_by(id=repo_id).first()
        if not repo:
            return {}

        total_commits = repo.total_commits
        total_files = repo.total_files
        total_loc = repo.total_lines_of_code
        contributors_count = session.query(Developer).filter_by(repository_id=repo_id).count()
        bug_fix_commits = session.query(Commit).filter_by(repository_id=repo_id, is_bug_fix=True).count()
        
        # Hotspot count: files with hotspot_score >= 40
        hotspots_count = (
            session.query(FileMetric)
            .join(File, FileMetric.file_id == File.id)
            .filter(File.repository_id == repo_id, FileMetric.hotspot_score >= 40.0)
            .count()
        )

        return {
            "name": repo.name,
            "url": repo.url,
            "default_branch": repo.default_branch,
            "analyzed_at": repo.analyzed_at,
            "total_commits": total_commits,
            "total_files": total_files,
            "contributors_count": contributors_count,
            "total_loc": total_loc,
            "bug_fix_commits": bug_fix_commits,
            "hotspots_count": hotspots_count,
        }


def get_commits_df(repo_id: int) -> pd.DataFrame:
    """Returns Pandas DataFrame of all commits for the repository."""
    with get_db_context() as session:
        commits = (
            session.query(Commit)
            .filter_by(repository_id=repo_id)
            .order_by(desc(Commit.commit_date))
            .all()
        )
        data = [
            {
                "Commit Hash": c.commit_hash[:7],
                "Full Hash": c.commit_hash,
                "Author": c.author_name,
                "Email": c.author_email,
                "Date": c.commit_date,
                "Files Changed": c.files_changed,
                "Lines Added": c.lines_added,
                "Lines Deleted": c.lines_deleted,
                "Net Lines": c.lines_added - c.lines_deleted,
                "Possible Bug Fix": "Yes" if c.is_bug_fix else "No",
                "Message": c.message.splitlines()[0] if c.message else "",
                "Full Message": c.message,
            }
            for c in commits
        ]
        return pd.DataFrame(data)


def get_files_df(repo_id: int) -> pd.DataFrame:
    """Returns Pandas DataFrame of files with activity and complexity metrics."""
    with get_db_context() as session:
        results = (
            session.query(File, FileMetric)
            .outerjoin(FileMetric, File.id == FileMetric.file_id)
            .filter(File.repository_id == repo_id)
            .order_by(desc(File.change_count))
            .all()
        )
        data = []
        for file_obj, metric in results:
            data.append({
                "File Path": file_obj.file_path,
                "File Name": file_obj.file_name,
                "Extension": file_obj.file_extension or "none",
                "Lines of Code (LOC)": metric.loc if metric else file_obj.current_loc,
                "SLOC": metric.sloc if metric else 0,
                "Comments": metric.comments if metric else 0,
                "Complexity (CC)": metric.cyclomatic_complexity if metric else 1.0,
                "Rank": metric.complexity_rank if metric else "A",
                "Commits": file_obj.change_count,
                "Bug Fixes": file_obj.bug_fix_count,
                "Lines Added": file_obj.lines_added,
                "Lines Deleted": file_obj.lines_deleted,
                "Hotspot Score": metric.hotspot_score if metric else 0.0,
                "Active": "Yes" if file_obj.is_active else "Deleted",
            })
        return pd.DataFrame(data)


def get_hotspots_df(repo_id: int) -> pd.DataFrame:
    """Returns Pandas DataFrame of files ranked by Hotspot Score."""
    with get_db_context() as session:
        results = (
            session.query(File, FileMetric)
            .join(FileMetric, File.id == FileMetric.file_id)
            .filter(File.repository_id == repo_id)
            .order_by(desc(FileMetric.hotspot_score))
            .all()
        )
        data = []
        for file_obj, metric in results:
            score = metric.hotspot_score
            if score >= 65:
                risk = "High"
            elif score >= 35:
                risk = "Medium"
            else:
                risk = "Low"

            reason = f"{file_obj.change_count} commits, {file_obj.bug_fix_count} bug fixes, CC {metric.cyclomatic_complexity} (Rank {metric.complexity_rank})"

            data.append({
                "File Path": file_obj.file_path,
                "Hotspot Score": score,
                "Risk Level": risk,
                "Complexity (CC)": metric.cyclomatic_complexity,
                "Complexity Rank": metric.complexity_rank,
                "Commits": file_obj.change_count,
                "Bug Fixes": file_obj.bug_fix_count,
                "LOC": metric.loc,
                "Reason / Heuristic": reason,
                "Lines Added": file_obj.lines_added,
                "Lines Deleted": file_obj.lines_deleted,
            })
        return pd.DataFrame(data)


def get_contributors_df(repo_id: int) -> pd.DataFrame:
    """Returns Pandas DataFrame of contributors."""
    with get_db_context() as session:
        contributors = (
            session.query(Developer)
            .filter_by(repository_id=repo_id)
            .order_by(desc(Developer.total_commits))
            .all()
        )
        data = []
        for dev in contributors:
            # Count distinct files changed by this developer
            files_touched = (
                session.query(func.count(func.distinct(CommitFile.file_id)))
                .join(Commit, CommitFile.commit_id == Commit.id)
                .filter(Commit.developer_id == dev.id)
                .scalar() or 0
            )

            data.append({
                "Contributor": dev.name,
                "Email": dev.email,
                "Commits": dev.total_commits,
                "Files Touched": files_touched,
                "Lines Added": dev.total_lines_added,
                "Lines Deleted": dev.total_lines_deleted,
                "Net Contribution": dev.total_lines_added - dev.total_lines_deleted,
                "First Commit": dev.first_commit_date.strftime("%Y-%m-%d") if dev.first_commit_date else "N/A",
                "Last Commit": dev.last_commit_date.strftime("%Y-%m-%d") if dev.last_commit_date else "N/A",
            })
        return pd.DataFrame(data)


def delete_repository(repo_id: int):
    """Deletes a repository and all cascaded children from MySQL."""
    with get_db_context() as session:
        repo = session.query(Repository).filter_by(id=repo_id).first()
        if repo:
            session.delete(repo)
