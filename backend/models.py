from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
try:
    from backend.database import Base
except ImportError:
    from database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    subject = Column(String(100), nullable=True, default="General", index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)



class ScrapedDocument(Base):
    __tablename__ = "scraped_documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String(768), nullable=False, unique=True, index=True)
    canonical_url = Column(String(768), nullable=False, index=True)
    title = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Store raw HTML or raw text
    content_type = Column(String(50), nullable=True)  # e.g., html, pdf
    mime_type = Column(String(100), nullable=True)  # e.g., text/html, application/pdf
    source_type = Column(String(50), nullable=True)  # web_page, pdf_document
    parent_url = Column(String(768), nullable=True)
    depth = Column(Integer, default=0)
    content_hash = Column(String(64), nullable=False, index=True)
    etag = Column(String(255), nullable=True)
    last_modified = Column(String(255), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_scraped_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(30), default="NEW", index=True)  # NEW, UNCHANGED, UPDATED, REMOVED, ERROR
    processing_status = Column(String(30), default="PENDING", index=True)  # PENDING, PROCESSING, PROCESSED, FAILED
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # versions relationship omitted to prevent duplicate mapping conflicts


class ScrapedDocumentVersion(Base):
    __tablename__ = "scraped_document_versions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("scraped_documents.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    change_type = Column(String(30), nullable=False)  # NEW, UPDATED, REMOVED


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="RUNNING", index=True)  # RUNNING, COMPLETED, FAILED
    pages_discovered = Column(Integer, default=0)
    pages_scraped = Column(Integer, default=0)
    new_documents = Column(Integer, default=0)
    updated_documents = Column(Integer, default=0)
    unchanged_documents = Column(Integer, default=0)
    removed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True, default=1)
    name = Column(String(255), nullable=True, default="Rajesh Gouda")
    usn = Column(String(50), nullable=True, default="4DM24AI038")
    semester = Column(String(100), nullable=False, default="5th Semester")
    branch = Column(String(100), nullable=False, default="AIML")
    branch_full = Column(String(255), nullable=True, default="Artificial Intelligence & Machine Learning (AIML)")
    subjects_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VTUUpdate(Base):
    __tablename__ = "vtu_updates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=False)
    time_posted = Column(String(100), nullable=False)
    badge_color = Column(String(50), default="blue")
    icon_type = Column(String(50), default="file")
    link = Column(String(768), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())



