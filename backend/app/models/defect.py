from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"))
    defect_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    defect_class: Mapped[str] = mapped_column("class", String(32))
    confidence: Mapped[float] = mapped_column(Float)
    bbox_x: Mapped[int] = mapped_column(Integer)
    bbox_y: Mapped[int] = mapped_column(Integer)
    bbox_w: Mapped[int] = mapped_column(Integer)
    bbox_h: Mapped[int] = mapped_column(Integer)
    iso_severity: Mapped[str] = mapped_column(String(16))
    tile_origin_row: Mapped[int] = mapped_column(Integer, default=0)
    tile_origin_col: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    engineer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inspection: Mapped["Inspection"] = relationship(back_populates="defects")
