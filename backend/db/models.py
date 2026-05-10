from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import enum
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://codesentinel:codesentinel123@localhost:5432/codesentinel")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SeverityEnum(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class ScanStatusEnum(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scans = relationship("Scan", back_populates="user")


class Repository(Base):
    __tablename__ = "repositories"
    id = Column(Integer, primary_key=True)
    github_repo_id = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    name = Column(String, nullable=False)
    installation_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scans = relationship("Scan", back_populates="repository")


class Scan(Base):
    __tablename__ = "scans"
    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pr_number = Column(Integer)
    pr_title = Column(String)
    commit_sha = Column(String)
    branch = Column(String)
    status = Column(Enum(ScanStatusEnum), default=ScanStatusEnum.pending)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    repository = relationship("Repository", back_populates="scans")
    user = relationship("User", back_populates="scans")
    findings = relationship("Finding", back_populates="scan")


class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    agent = Column(String, nullable=False)
    rule_id = Column(String)
    title = Column(String, nullable=False)
    description = Column(Text)
    severity = Column(Enum(SeverityEnum), nullable=False)
    file_path = Column(String)
    line_start = Column(Integer)
    line_end = Column(Integer)
    code_snippet = Column(Text)
    fix_suggestion = Column(Text)
    ai_explanation = Column(Text)
    cwe_id = Column(String)  # Store as plain string
    raw_output = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    scan = relationship("Scan", back_populates="findings")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
