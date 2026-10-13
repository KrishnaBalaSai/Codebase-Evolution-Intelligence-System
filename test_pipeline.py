"""
End-to-End Pipeline Integration Test.
Tests Git clone, commit extraction, Radon metrics, hotspot calculation,
and MySQL database persistence on a real public repository.
"""

import sys
from database import test_connection, init_db, get_db_context
from models import Repository, Developer, Commit, File, CommitFile, FileMetric
from analysis import run_repository_analysis, get_repository_summary, get_commits_df, get_files_df, get_hotspots_df


def test_full_pipeline():
    print("Step 1: Testing MySQL connection...")
    ok, msg = test_connection()
    assert ok, f"Database connection failed: {msg}"
    print(f"  [OK] {msg}")

    print("Step 2: Initializing database tables...")
    init_db()
    print("  [OK] Tables initialized successfully.")

    print("Step 3: Running repository analysis on 'https://github.com/octocat/Spoon-Knife'...")
    test_repo_url = "https://github.com/octocat/Spoon-Knife"
    
    def log_progress(frac, msg):
        print(f"  Progress {int(frac*100)}%: {msg}")

    repo_id = run_repository_analysis(test_repo_url, progress_callback=log_progress)
    print(f"  [OK] Repository analyzed successfully. Assigned repo_id = {repo_id}")

    print("Step 4: Verifying database records...")
    with get_db_context() as session:
        repo = session.query(Repository).filter_by(id=repo_id).first()
        dev_count = session.query(Developer).filter_by(repository_id=repo_id).count()
        commit_count = session.query(Commit).filter_by(repository_id=repo_id).count()
        file_count = session.query(File).filter_by(repository_id=repo_id).count()
        metric_count = session.query(FileMetric).join(File, FileMetric.file_id == File.id).filter(File.repository_id == repo_id).count()
        
        print(f"  Repo: {repo.name} ({repo.url})")
        print(f"  Developers count: {dev_count}")
        print(f"  Commits count: {commit_count}")
        print(f"  Files count: {file_count}")
        print(f"  File metrics count: {metric_count}")

        assert commit_count > 0, "No commits stored!"
        assert file_count > 0, "No files stored!"
        assert metric_count > 0, "No metrics stored!"

    print("Step 5: Verifying analysis query dataframes...")
    summary = get_repository_summary(repo_id)
    commits_df = get_commits_df(repo_id)
    files_df = get_files_df(repo_id)
    hotspots_df = get_hotspots_df(repo_id)

    print(f"  Summary: {summary}")
    print(f"  Commits DF shape: {commits_df.shape}")
    print(f"  Files DF shape: {files_df.shape}")
    print(f"  Hotspots DF shape: {hotspots_df.shape}")

    assert not commits_df.empty, "Commits DF is empty!"
    assert not files_df.empty, "Files DF is empty!"
    assert not hotspots_df.empty, "Hotspots DF is empty!"

    print("\nALL INTEGRATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_full_pipeline()
