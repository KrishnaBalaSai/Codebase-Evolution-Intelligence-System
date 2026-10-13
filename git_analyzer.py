"""
Git repository analyzer using GitPython.
Clones or updates public Git repositories and extracts commits, file changes,
and active repository tree information.
"""

import os
import re
import shutil
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple, Any
import git
from git import Repo, RemoteProgress

# Regex for heuristic bug-fix commit detection
BUG_FIX_REGEX = re.compile(
    r"\b(fix|fixed|fixes|fixing|bug|bugs|error|errors|issue|issues|hotfix|hotfixes|patch|resolve|resolved)\b",
    re.IGNORECASE
)


class CloneProgress(RemoteProgress):
    """Callback adapter for GitPython remote progress reporting."""

    def __init__(self, callback: Optional[Callable[[float, str], None]] = None):
        super().__init__()
        self.callback = callback

    def update(self, op_code, cur_count, max_count=None, message=""):
        if self.callback and max_count:
            fraction = cur_count / max_count
            stage_name = self._cur_stage_name(op_code)
            detail = f"{stage_name}: {int(fraction * 100)}% ({cur_count}/{max_count}) {message}".strip()
            self.callback(fraction, detail)

    def _cur_stage_name(self, op_code: int) -> str:
        if op_code & RemoteProgress.COUNTING:
            return "Counting objects"
        if op_code & RemoteProgress.COMPRESSING:
            return "Compressing objects"
        if op_code & RemoteProgress.RECEIVING:
            return "Receiving objects"
        if op_code & RemoteProgress.RESOLVING:
            return "Resolving deltas"
        if op_code & RemoteProgress.WRITING:
            return "Writing objects"
        return "Cloning"


def parse_github_url(url: str) -> Tuple[bool, str, str]:
    """
    Validates and normalizes a GitHub or Git URL.
    Returns (is_valid, normalized_url, repo_name).
    """
    cleaned = url.strip()
    if not cleaned:
        return False, "", "Repository URL cannot be empty."

    # Pattern for https/http/ssh github urls
    github_pattern = re.compile(
        r"^(https?://github\.com/|git@github\.com:)(?P<owner>[\w\.\-]+)/(?P<repo>[\w\.\-]+?)(\.git)?/?$",
        re.IGNORECASE
    )
    match = github_pattern.match(cleaned)
    if match:
        owner = match.group("owner")
        repo = match.group("repo")
        norm_url = f"https://github.com/{owner}/{repo}.git"
        display_name = f"{owner}/{repo}"
        return True, norm_url, display_name

    # General git URL check
    general_pattern = re.compile(r"^(https?://|git@).+/(?P<repo>[\w\.\-]+?)(\.git)?/?$")
    gmatch = general_pattern.match(cleaned)
    if gmatch:
        repo = gmatch.group("repo")
        norm_url = cleaned if cleaned.endswith(".git") else f"{cleaned}.git"
        return True, norm_url, repo

    return False, "", "Invalid GitHub repository URL format. Example: https://github.com/psf/requests"


def get_repo_clone_path(repo_url: str, base_dir: str = "./cloned_repos") -> str:
    """Computes a safe local directory path for cloning the repository."""
    os.makedirs(base_dir, exist_ok=True)
    # Sanitize URL to create directory name
    safe_name = re.sub(r"[^\w\-]", "_", repo_url.replace("https://", "").replace("http://", "").replace(".git", ""))
    return os.path.abspath(os.path.join(base_dir, safe_name))


def clone_or_open_repository(
    repo_url: str,
    target_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Repo:
    """
    Clones a Git repository from repo_url or opens it if already present.
    If corrupted, removes the directory and clones afresh.
    """
    if not target_dir:
        target_dir = get_repo_clone_path(repo_url)

    if os.path.exists(target_dir):
        try:
            repo = Repo(target_dir)
            if not repo.bare and repo.git_dir:
                if progress_callback:
                    progress_callback(0.1, "Existing local repository found. Fetching latest changes...")
                try:
                    repo.remotes.origin.fetch()
                except Exception:
                    # If fetch fails (e.g. offline or auth), proceed with existing data
                    pass
                return repo
        except Exception:
            # Corrupted directory, remove and re-clone
            if progress_callback:
                progress_callback(0.05, "Cleaning up invalid local clone...")
            shutil.rmtree(target_dir, ignore_errors=True)

    if progress_callback:
        progress_callback(0.05, f"Cloning repository into {os.path.basename(target_dir)}...")

    progress = CloneProgress(progress_callback)
    repo = Repo.clone_from(repo_url, target_dir, progress=progress)
    return repo


def is_bug_fix_commit(message: str) -> bool:
    """
    Heuristically checks if a commit message indicates a bug fix
    using keywords: fix, bug, error, issue, hotfix, patch, resolve.
    """
    if not message:
        return False
    return bool(BUG_FIX_REGEX.search(message))


def extract_git_history(
    repo: Repo,
    max_commits: int = 2000,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Extracts commit history, file modifications, and developer metrics from a Git repository.
    """
    default_branch = repo.active_branch.name if not repo.head.is_detached else "HEAD"

    # Get commits from default branch
    try:
        commits_iterable = list(repo.iter_commits(default_branch, max_count=max_commits))
    except Exception:
        commits_iterable = list(repo.iter_commits("HEAD", max_count=max_commits))

    total_commit_count = len(commits_iterable)
    commits_data: List[Dict[str, Any]] = []
    developers_dict: Dict[str, Dict[str, Any]] = {}
    files_dict: Dict[str, Dict[str, Any]] = {}

    for idx, commit in enumerate(commits_iterable):
        if progress_callback and idx % 25 == 0:
            pct = 0.2 + 0.6 * (idx / max(1, total_commit_count))
            progress_callback(pct, f"Analyzing commit {idx + 1} of {total_commit_count}...")

        commit_hash = commit.hexsha
        author_name = commit.author.name or "Unknown"
        author_email = (commit.author.email or f"{author_name}@unknown.local").lower()
        message = commit.message.strip() if commit.message else ""
        
        # GitPython commit time is timestamp; convert to naive UTC datetime
        commit_dt = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc).replace(tzinfo=None)
        
        is_bug_fix = is_bug_fix_commit(message)

        # Developer aggregation
        dev_key = author_email
        if dev_key not in developers_dict:
            developers_dict[dev_key] = {
                "name": author_name,
                "email": author_email,
                "total_commits": 0,
                "total_lines_added": 0,
                "total_lines_deleted": 0,
                "first_commit_date": commit_dt,
                "last_commit_date": commit_dt,
            }
        dev_stat = developers_dict[dev_key]
        dev_stat["total_commits"] += 1
        if commit_dt < dev_stat["first_commit_date"]:
            dev_stat["first_commit_date"] = commit_dt
        if commit_dt > dev_stat["last_commit_date"]:
            dev_stat["last_commit_date"] = commit_dt

        # Parse stats
        lines_added = 0
        lines_deleted = 0
        commit_files: List[Dict[str, Any]] = []

        try:
            stats = commit.stats
            lines_added = stats.total.get("insertions", 0)
            lines_deleted = stats.total.get("deletions", 0)
            files_stat = stats.files

            for file_path, file_stat in files_stat.items():
                file_path = file_path.replace("\\", "/").strip()
                f_added = file_stat.get("insertions", 0)
                f_deleted = file_stat.get("deletions", 0)

                # Initialize or update file tracking
                if file_path not in files_dict:
                    base_name = os.path.basename(file_path)
                    ext = os.path.splitext(base_name)[1].lower()
                    files_dict[file_path] = {
                        "file_path": file_path,
                        "file_name": base_name,
                        "file_extension": ext,
                        "change_count": 0,
                        "lines_added": 0,
                        "lines_deleted": 0,
                        "bug_fix_count": 0,
                        "current_loc": 0,
                        "is_active": False,
                    }

                f_info = files_dict[file_path]
                f_info["change_count"] += 1
                f_info["lines_added"] += f_added
                f_info["lines_deleted"] += f_deleted
                if is_bug_fix:
                    f_info["bug_fix_count"] += 1

                commit_files.append({
                    "file_path": file_path,
                    "change_type": "M",  # Modified
                    "lines_added": f_added,
                    "lines_deleted": f_deleted
                })

        except Exception:
            # Fallback if commit.stats raises on specific merges or root commits
            pass

        dev_stat["total_lines_added"] += lines_added
        dev_stat["total_lines_deleted"] += lines_deleted

        commits_data.append({
            "commit_hash": commit_hash,
            "author_name": author_name,
            "author_email": author_email,
            "message": message,
            "commit_date": commit_dt,
            "files_changed": len(commit_files),
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "is_bug_fix": is_bug_fix,
            "commit_files": commit_files,
        })

    # Now inspect active files in latest commit (HEAD)
    if progress_callback:
        progress_callback(0.85, "Scanning active files in repository tree...")

    active_files_count = 0
    try:
        head_commit = repo.head.commit
        for item in head_commit.tree.traverse():
            if item.type == "blob":
                active_files_count += 1
                file_path = item.path.replace("\\", "/").strip()
                base_name = os.path.basename(file_path)
                ext = os.path.splitext(base_name)[1].lower()

                # Approximate LOC for active file
                loc = 0
                try:
                    data = item.data_stream.read()
                    loc = len(data.splitlines())
                except Exception:
                    pass

                if file_path not in files_dict:
                    files_dict[file_path] = {
                        "file_path": file_path,
                        "file_name": base_name,
                        "file_extension": ext,
                        "change_count": 0,
                        "lines_added": 0,
                        "lines_deleted": 0,
                        "bug_fix_count": 0,
                        "current_loc": loc,
                        "is_active": True,
                    }
                else:
                    files_dict[file_path]["is_active"] = True
                    files_dict[file_path]["current_loc"] = loc
    except Exception:
        pass

    return {
        "default_branch": default_branch,
        "total_commits": total_commit_count,
        "total_files": len(files_dict),
        "active_files_count": active_files_count,
        "commits": commits_data,
        "developers": list(developers_dict.values()),
        "files": list(files_dict.values()),
    }
