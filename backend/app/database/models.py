import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base

class Standard(Base):
    __tablename__ = "standards"

    id = Column(Integer, primary_key=True, index=True)
    standard_number = Column(String(100), unique=True, index=True, nullable=False) # e.g. IS 1011, IS 16221 (Part 1)
    title = Column(String(500), index=True, nullable=False)
    publication_year = Column(Integer, nullable=True)
    reaffirmed_year = Column(Integer, nullable=True) # Reviewed In / Reaffirmed Year
    no_of_amendments = Column(Integer, default=0) # Number of amendments
    revision_count = Column(Integer, default=0) # Number of revisions (e.g. 1 for First Revision, 6 for Sixth)
    revision_text = Column(String(100), default="Original Publication") # e.g. "Sixth Revision"
    supersedes_is = Column(String(200), nullable=True) # What older standard this replaces
    superseded_by_is = Column(String(200), nullable=True) # Whether replaced by newer standard
    certification_scheme = Column(String(100), default="Mandatory ISI Scheme-I") # Mandatory ISI / CRS / Voluntary
    scope = Column(Text, nullable=True)
    ics_code = Column(String(50), index=True, nullable=True) # e.g. 67.060
    committee_code = Column(String(50), index=True, nullable=True) # e.g. FAD 24, ETD 28, CED 2
    domain = Column(String(100), index=True, nullable=True) # Food, Electrical, Civil, etc.
    status = Column(String(50), default="Active", index=True) # Active, Reaffirmed, Withdrawn, Superseded
    is_mandatory = Column(Boolean, default=False)
    
    # Provenance and source URLs
    source_url = Column(String(500), nullable=True)
    preview_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_verified_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    references = relationship("StandardReference", back_populates="standard", cascade="all, delete-orphan")
    amendments = relationship("Amendment", back_populates="standard", cascade="all, delete-orphan")
    safety_testing = relationship("SafetyTestingMetadata", back_populates="standard", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_std_num_title', 'standard_number', 'title'),
        Index('idx_domain_status', 'domain', 'status'),
    )

class StandardReference(Base):
    __tablename__ = "standard_references"

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False, index=True)
    referenced_standard_number = Column(String(100), index=True, nullable=False) # e.g. IS 253
    referenced_title = Column(String(500), nullable=True)
    referenced_year = Column(Integer, nullable=True)
    reference_type = Column(String(50), default="normative") # normative, raw_material, testing, safety, packaging
    link = Column(String(500), nullable=True)

    standard = relationship("Standard", back_populates="references")

class Amendment(Base):
    __tablename__ = "amendments"

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False, index=True)
    amendment_number = Column(String(50), nullable=False) # e.g. "Amd. 1", "Amd. 2"
    amendment_year = Column(Integer, nullable=True) # Amendment year
    publication_date = Column(String(50), nullable=True) # e.g. "4/24/2018", "1/17/2023"
    committee_code = Column(String(50), nullable=True) # e.g. "CED 15", "FAD 24"
    title = Column(String(500), nullable=True)
    status = Column(String(50), default="Active")
    source_url = Column(String(500), nullable=True)

    standard = relationship("Standard", back_populates="amendments")

class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False) # e.g. FAD 24, CED 2
    classification_type = Column(String(50), index=True) # ICS, COMMITTEE, DOMAIN
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

class SafetyTestingMetadata(Base):
    __tablename__ = "safety_testing_metadata"

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), unique=True, nullable=False)
    is_safety_related = Column(Boolean, default=False, index=True)
    is_testing_related = Column(Boolean, default=False, index=True)
    is_sampling_related = Column(Boolean, default=False)
    is_quality_spec = Column(Boolean, default=True)
    safety_justification = Column(Text, nullable=True)
    testing_methods_summary = Column(Text, nullable=True)
    source_type = Column(String(50), default="rule_based") # official, rule_based, ai_inferred

    standard = relationship("Standard", back_populates="safety_testing")

class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id = Column(Integer, primary_key=True, index=True)
    standard_number = Column(String(100), index=True)
    action = Column(String(50))
    status = Column(String(50))
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
