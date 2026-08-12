from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id"))
    inspection_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    image_path: Mapped[str] = mapped_column(String(512))
    tile_size: Mapped[int] = mapped_column(Integer, default=640)
    overlap_margin: Mapped[int] = mapped_column(Integer, default=64)
    conf_threshold: Mapped[float] = mapped_column(Float, default=0.25)
    iou_threshold: Mapped[float] = mapped_column(Float, default=0.45)
    board_disposition: Mapped[str] = mapped_column(String(20), default="CONFORMING")
    schema_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    cycle_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="PROCESSING")  # PROCESSING|COMPLETE|FAILED
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    board: Mapped["Board"] = relationship(back_populates="inspections")
    defects: Mapped[list["Defect"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    narrative: Mapped["Narrative"] = relationship(back_populates="inspection", uselist=False, cascade="all, delete-orphan")
