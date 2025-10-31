"""SQLAlchemy models for the reagent-ology backend."""
from __future__ import annotations

import json
from datetime import datetime, date
from typing import List

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Reagent(Base):
    """Chemical reagent stored in the laboratory inventory."""

    __tablename__ = "reagents"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    formula = Column(String(255), nullable=False)
    cas = Column(String(64))
    location = Column(String(255), nullable=False)
    storage = Column(String(255))
    expiry = Column(Date)
    hazard = Column(String(255))
    ghs = Column(Text, nullable=False, default="[]")
    disposal = Column(String(255))
    density = Column(Float)
    volume_ml = Column(Float)
    nfc_tag_uid = Column(String(128), unique=True)
    scale_device = Column(String(128))
    quantity = Column(Float, nullable=False, default=0.0)
    used = Column(Float, nullable=False, default=0.0)
    discarded = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    usage_logs = relationship(
        "UsageLog",
        back_populates="reagent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Utility helpers -----------------------------------------------------
    def ghs_list(self) -> List[str]:
        try:
            return json.loads(self.ghs or "[]")
        except json.JSONDecodeError:
            return []

    def set_ghs(self, values: List[str]) -> None:
        self.ghs = json.dumps(values or [])


class UsageLog(Base):
    """Tracks quantity adjustments for a reagent."""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    reagent_id = Column(
        Integer,
        ForeignKey("reagents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prev_qty = Column(Float, nullable=False)
    new_qty = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)
    source = Column(String(64), default="manual", nullable=False)
    note = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    reagent = relationship("Reagent", back_populates="usage_logs")
