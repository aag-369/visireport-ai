from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_version: Mapped[str] = mapped_column(String(64))
    map50: Mapped[float] = mapped_column(Float)
    map50_95: Mapped[float] = mapped_column(Float)
    precision: Mapped[float] = mapped_column(Float)
    recall: Mapped[float] = mapped_column(Float)
    per_class_metrics_json: Mapped[str | None] = mapped_column(String, nullable=True)
    dataset: Mapped[str] = mapped_column(String(128), default="DeepPCB")
    epochs: Mapped[int] = mapped_column(Float, default=0)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
