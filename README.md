# 🧬 Codebase Evolution Intelligence System

A software engineering analytics platform built with **Python**, **MySQL**, **Streamlit**, **GitPython**, **Pandas**, **Plotly**, and **Radon**.

This system allows developers, technical leads, and engineering managers to analyze the evolution history of any public Git/GitHub repository. It extracts commits, file churn, and author contributions, analyzes Python code complexity using **Radon**, identifies high-maintenance **Code Hotspots**, and presents actionable visual intelligence through an interactive dashboard.

---

## 🎯 Problem Statement & Motivation

Git repositories store years of rich software evolution history. However, developers and engineering teams face significant challenges in understanding:
- **Which files change too frequently?** (High churn indicating unstable abstractions or volatile requirements).
- **Where are bugs concentrating?** (Files frequently touched in bug-fixing commits).
- **Which components are overly complex?** (High cyclomatic complexity requiring refactoring).
- **Who are the key contributors?** (Knowledge distribution and bus factor).
- **How is the codebase growing over time?** (Velocity, line churn, additions vs. deletions).

Manually running `git log` and `git diff` does not provide this holistic picture. **Codebase Evolution Intelligence System** solves this by automating the extraction, storage in MySQL, complexity computation, and interactive visualization.

---

## 🚀 Key Features

### 1. Repository Ingestion & Cloning
- Accepts any public Git or GitHub URL (e.g., `https://github.com/pallets/flask`).
- Clones and updates repositories automatically using **GitPython**.
- Real-time progress bar reporting clone and analysis stages.

### 2. Commit Analysis
- Tracks commit hash, author name, author email, commit date, and commit message.
- Tracks files changed, lines added (+), and lines deleted (-).
- Interactive filters: search by message/hash, filter by author, sort by date/churn, and filter by bug-fix commits.

### 3. File & Churn Analysis
- Tracks total lines of code (LOC), source lines of code (SLOC), and comments.
- Tracks modification frequency (commit count per file) and churn.
- Scatter plots mapping churn against file size and complexity.

### 4. Code Complexity (Radon)
- Uses **Radon** to compute **Cyclomatic Complexity (CC)** and complexity grades (`A` through `F`) for Python files.
- Highlights functions, methods, and classes that exceed standard complexity thresholds.

### 5. Heuristic Bug-Fix Analysis
- Identifies bug-fixing commits using targeted keyword heuristics (`fix`, `bug`, `error`, `issue`, `hotfix`, `patch`).
- Maps bug-fix activity over time.
- Clearly labeled as *"Possible Bug-Fix Commits"* to maintain transparency regarding heuristic detection.

### 6. Multi-Factor Code Hotspots
- Automatically calculates a composite **Hotspot Score (0 to 100)**:
  $$\text{Hotspot Score} = (0.40 \times \text{NormChurn}) + (0.35 \times \text{NormBugs}) + (0.25 \times \text{NormComplexity}) \times 100$$
- Categorizes files into **High Risk (≥65)**, **Medium Risk (35–64)**, and **Low Risk / Stable (<35)**.
- Provides human-readable explanations detailing why a specific file was flagged and provides actionable refactoring recommendations.

### 7. Contributor Intelligence
- Computes commits per contributor, files touched, lines added, lines deleted, and net code contributions.
- Visualizes top contributor rankings and commit share distribution (pie/donut charts).

### 8. Codebase Evolution Visualizations
- Interactive **Plotly** charts:
  - Commit velocity over time with rolling moving average.
  - Lines added vs. lines deleted over time (churn dynamics).
  - Cumulative net codebase growth (LOC growth curve).
  - Heuristic bug-fix commits timeline.
  - Active contributor count trends over time.

---

## 🏗️ System Architecture & Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **User Interface** | Streamlit | Clean, modern light-theme multi-page interactive web dashboard |
| **Visualizations** | Plotly Express & Graph Objects | Dynamic, responsive charts (scatter, bars, pies, timelines) |
| **Git Engine** | GitPython | Autonomous cloning, commit traversal, and tree inspection |
| **Metrics Engine** | Radon | Cyclomatic complexity (CC) and raw line analysis (LOC/SLOC) |
| **Data Processing** | Pandas | Tabular data manipulation, time-series resampling, and filtering |
| **Database** | MySQL 8.0 & SQLAlchemy | Relational persistence with foreign keys, cascading deletes, and indexing |
| **Configuration** | python-dotenv | Secure credential management via `.env` |

---

## 🗄️ Database Schema

The database `codebase_evolution` consists of 6 relational tables with primary keys, foreign keys, cascading deletes, and indexes:

```text
repositories (1) ────< (M) developers (1) ────< (M) commits
     │                                                   │
     │ (1)                                               │ (1)
     │                                                   │
     v (M)                                               v (M)
   files (1) ─────────────< (M) commit_files >───────────┘
     │
     │ (1)
     v (1)
 file_metrics
```

### Table Details:
1. **`repositories`**: Stores repository metadata (`id`, `name`, `url`, `default_branch`, `total_commits`, `total_files`, `total_lines_of_code`, `analyzed_at`).
2. **`developers`**: Stores contributors (`id`, `repository_id`, `name`, `email`, `total_commits`, `total_lines_added`, `total_lines_deleted`, `first_commit_date`, `last_commit_date`).
3. **`commits`**: Stores commit records (`id`, `repository_id`, `developer_id`, `commit_hash`, `author_name`, `message`, `commit_date`, `lines_added`, `lines_deleted`, `is_bug_fix`).
4. **`files`**: Tracks unique file paths in the repository (`id`, `repository_id`, `file_path`, `file_name`, `file_extension`, `change_count`, `lines_added`, `lines_deleted`, `bug_fix_count`, `is_active`).
5. **`commit_files`**: Associative junction table between commits and files (`id`, `commit_id`, `file_id`, `change_type`, `lines_added`, `lines_deleted`).
6. **`file_metrics`**: Stores computed complexity metrics (`id`, `file_id`, `loc`, `sloc`, `comments`, `cyclomatic_complexity`, `complexity_rank`, `hotspot_score`, `analyzed_at`).

---

## 📁 Project Structure

```text
codebase-evolution/
│
├── app.py                  # Main Streamlit application & sidebar routing
├── database.py             # MySQL engine, connection pooling, and table creation
├── models.py               # SQLAlchemy ORM declarative models
├── git_analyzer.py         # GitPython repository cloner & commit parser
├── metrics.py              # Radon complexity & hotspot scoring algorithm
├── analysis.py             # Orchestration pipeline and query layer
├── test_pipeline.py        # End-to-end integration test suite
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── .env                    # Active database credentials
├── README.md               # Project documentation & interview guide
│
└── pages/
    ├── overview.py         # KPI cards & high-level summary charts
    ├── commits.py          # Commit search, filter, and inspector
    ├── files.py            # File modification frequency & Radon metrics
    ├── hotspots.py         # Multi-factor hotspot scoring & recommendations
    ├── contributors.py     # Contributor rankings & code ownership
    └── evolution.py        # Interactive Plotly time-series evolution charts
```

---

## ⚙️ Installation & Setup

### Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **Git** installed and available in PATH
- **MySQL Server 8.0+** running locally or remotely

### Step 1: Clone or Navigate to Project Directory
```powershell
cd "c:\Users\srini\OneDrive\Desktop\Code Evolution AI System"
```

### Step 2: Set Up Virtual Environment & Dependencies
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (Command Prompt):
.\venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` (or update existing `.env`):
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=codebase_evolution
REPOS_DIR=./cloned_repos
```
*(The system automatically creates the `codebase_evolution` database in MySQL if it doesn't already exist!)*

### Step 4: Run the Streamlit Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🖥️ How to Use

1. **Verify Database Connection:** Look at the top of the sidebar. You should see `🟢 MySQL Connected`.
2. **Analyze a Repository:**
   - Paste any public GitHub URL (e.g., `https://github.com/pallets/flask` or `https://github.com/psf/requests`).
   - Or click one of the quick test presets (`psf/requests`, `pallets/flask`).
   - Click **"🚀 Analyze Repository"**.
3. **Monitor Progress:** The progress bar displays cloning, commit parsing, Radon complexity analysis, and database storage steps.
4. **Explore the Dashboard:**
   - **Overview:** View high-level KPIs (Total Commits, LOC, Contributors, Bug Fixes, Hotspots).
   - **Commits:** Search commits, inspect diffs, and toggle bug-fix filters.
   - **Files:** View files sorted by change count and inspect Radon cyclomatic complexity.
   - **Hotspots:** Investigate files flagged with high hotspot scores and review refactoring guidance.
   - **Contributors:** Review contributor leaderboard, lines added vs. deleted, and commit share.
   - **Evolution:** Inspect long-term velocity, code churn, net growth, and contributor trends.

---

## 🎓 Technical Interview Guide & Explanations

When presenting this project in a technical interview, use these talking points:

### Q1: Why did you design the hotspot score using three specific dimensions?
> **Answer:** "A single metric is misleading. A file with high complexity isn't a problem if nobody ever touches it. A file with frequent changes might just be a configuration or documentation file. A true code hotspot is at the intersection of:
> 1. **High Churn (40%):** Developers are frequently modifying it.
> 2. **High Bug Fixes (35%):** Changes frequently introduce defects or require bug patches.
> 3. **High Cyclomatic Complexity (25%):** The internal logic contains many decision branches (`if`, `for`, `while`), making modifications error-prone.
> By normalizing each factor and computing a weighted composite score, we provide actionable guidance on which files present the highest maintenance debt."

### Q2: Why is keyword detection labeled as a 'Heuristic' for bug fixes?
> **Answer:** "Commit messages like `'fix bug in auth'` or `'resolve issue #42'` correlate strongly with bug fixes, but natural language commit messages can also contain false positives (e.g., `'fixed formatting'`) or false negatives (e.g., `'address edge case'`). Explicitly labeling it as a heuristic is an important software engineering best practice that sets realistic expectations."

### Q3: Why use Radon for Cyclomatic Complexity?
> **Answer:** "Radon is a mature static analysis tool for Python that computes McCabe Cyclomatic Complexity by parsing the Python Abstract Syntax Tree (AST). It gives precise decision-point counts and assigns industry-standard ranks (`A` for simple functions up to `F` for dangerously complex code) without executing the code."

### Q4: How is database performance maintained for large repositories?
> **Answer:** "We use SQLAlchemy connection pooling (`pool_pre_ping=True`, `pool_recycle=3600`) and index all foreign keys, commit hashes, file paths, and dates. When bulk inserting commit-file links, we utilize `bulk_save_objects` to avoid single-row roundtrips."
