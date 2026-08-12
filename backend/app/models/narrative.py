from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Narrative(Base):
    __tablename__ = "narratives"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), unique=True)
    narrative_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    capa_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded CAPA sections
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING|READY|FAILED
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    llm_model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    inspection: Mapped["Inspection"] = relationship(back_populates="narrative")
