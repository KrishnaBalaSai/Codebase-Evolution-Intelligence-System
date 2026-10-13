"""
SQLAlchemy models for Codebase Evolution Intelligence System.
Defines schema for repositories, developers, commits, files, commit_files, and file_metrics.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Repository(Base):
    """Represents an analyzed Git/GitHub repository."""
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False, unique=True, index=True)
    default_branch = Column(String(100), default="main")
    cloned_path = Column(String(500), nullable=True)
    total_commits = Column(Integer, default=0)
    total_files = Column(Integer, default=0)
    total_lines_of_code = Column(Integer, default=0)
    analyzed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    developers = relationship("Developer", back_populates="repository", cascade="all, delete-orphan")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    files = relationship("File", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Repository(id={self.id}, name='{self.name}', url='{self.url}')>"


class Developer(Base):
    """Represents a contributor / committer to a repository."""
    __tablename__ = "developers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    total_commits = Column(Integer, default=0)
    total_lines_added = Column(Integer, default=0)
    total_lines_deleted = Column(Integer, default=0)
    first_commit_date = Column(DateTime, nullable=True)
    last_commit_date = Column(DateTime, nullable=True)

    # Relationships
    repository = relationship("Repository", back_populates="developers")
    commits = relationship("Commit", back_populates="developer")

    __table_args__ = (
        UniqueConstraint("repository_id", "email", name="uq_repo_developer_email"),
    )

    def __repr__(self):
        return f"<Developer(id={self.id}, name='{self.name}', email='{self.email}')>"


class Commit(Base):
    """Represents a Git commit with author, stats, and bug-fix heuristic flag."""
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    developer_id = Column(Integer, ForeignKey("developers.id", ondelete="SET NULL"), nullable=True, index=True)
    commit_hash = Column(String(40), nullable=False, index=True)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    commit_date = Column(DateTime, nullable=False, index=True)
    files_changed = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    is_bug_fix = Column(Boolean, default=False, index=True)

    # Relationships
    repository = relationship("Repository", back_populates="commits")
    developer = relationship("Developer", back_populates="commits")
    commit_files = relationship("CommitFile", back_populates="commit", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("repository_id", "commit_hash", name="uq_repo_commit_hash"),
    )

    def __repr__(self):
        return f"<Commit(hash='{self.commit_hash[:7]}', author='{self.author_name}', date='{self.commit_date}')>"


class File(Base):
    """Represents a file tracked in the repository."""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500, collation="utf8mb4_bin"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_extension = Column(String(50), nullable=True)
    current_loc = Column(Integer, default=0)
    change_count = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    bug_fix_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Relationships
    repository = relationship("Repository", back_populates="files")
    commit_files = relationship("CommitFile", back_populates="file", cascade="all, delete-orphan")
    metrics = relationship("FileMetric", back_populates="file", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("repository_id", "file_path", name="uq_repo_file_path"),
    )

    def __repr__(self):
        return f"<File(id={self.id}, path='{self.file_path}', changes={self.change_count})>"


class CommitFile(Base):
    """Represents a many-to-many relationship between a commit and the files it touched."""
    __tablename__ = "commit_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type = Column(String(20), default="M")  # 'A' (added), 'M' (modified), 'D' (deleted), 'R' (renamed)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)

    # Relationships
    commit = relationship("Commit", back_populates="commit_files")
    file = relationship("File", back_populates="commit_files")

    def __repr__(self):
        return f"<CommitFile(commit_id={self.commit_id}, file_id={self.file_id}, change='{self.change_type}')>"


class FileMetric(Base):
    """Represents Radon complexity metrics and calculated hotspot scores for a file."""
    __tablename__ = "file_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    loc = Column(Integer, default=0)
    sloc = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    cyclomatic_complexity = Column(Float, default=0.0)
    complexity_rank = Column(String(5), default="A")  # Radon ranks: A, B, C, D, E, F
    change_count = Column(Integer, default=0)
    bug_fix_count = Column(Integer, default=0)
    hotspot_score = Column(Float, default=0.0)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    file = relationship("File", back_populates="metrics")

    def __repr__(self):
        return f"<FileMetric(file_id={self.file_id}, complexity={self.cyclomatic_complexity}, rank='{self.complexity_rank}', hotspot={self.hotspot_score})>"
