from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.infrastructure.persistence.base import Base

class DBSecurityFinding(Base):
    __tablename__ = "security_findings"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(String, ForeignKey("code_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    vulnerability = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    cwe_id = Column(String, nullable=False)
    owasp_category = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    attack_scenario = Column(Text, nullable=False)
    suggested_fix = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)

    review = relationship("DBCodeReview", back_populates="security_findings")
