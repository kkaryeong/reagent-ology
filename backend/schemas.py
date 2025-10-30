"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class UsageLogBase(BaseModel):
    prev_qty: float
    new_qty: float
    delta: float
    source: str = Field(default="manual", max_length=64)
    note: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime


class UsageLogOut(UsageLogBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ReagentBase(BaseModel):
    name: str = Field(..., max_length=255)
    formula: str = Field(..., max_length=255)
    cas: Optional[str] = Field(default=None, max_length=64)
    location: str = Field(..., max_length=255)
    storage: Optional[str] = Field(default=None, max_length=255)
    expiry: Optional[date] = None
    hazard: Optional[str] = Field(default=None, max_length=255)
    ghs: List[str] = Field(default_factory=list)
    disposal: Optional[str] = Field(default=None, max_length=255)
    quantity: float = 0.0
    used: float = 0.0
    discarded: float = 0.0


class ReagentCreate(ReagentBase):
    pass


class ReagentUpdate(BaseModel):
    name: Optional[str] = None
    formula: Optional[str] = None
    cas: Optional[str] = None
    location: Optional[str] = None
    storage: Optional[str] = None
    expiry: Optional[date] = None
    hazard: Optional[str] = None
    ghs: Optional[List[str]] = None
    disposal: Optional[str] = None
    quantity: Optional[float] = None
    used: Optional[float] = None
    discarded: Optional[float] = None


class ReagentOut(ReagentBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UseRequest(BaseModel):
    amount: float = Field(..., gt=0)
    note: Optional[str] = Field(default=None, max_length=255)


class MeasurementRequest(BaseModel):
    new_quantity: float = Field(..., ge=0)
    source: str = Field(default="scale", max_length=64)
    note: Optional[str] = Field(default=None, max_length=255)


class AutocompleteItem(BaseModel):
    name: str
    formula: Optional[str]
    cid: Optional[int]


class AutocompleteResponse(BaseModel):
    suggestions: List[AutocompleteItem]


# Local autocomplete DB management
class LocalChemBase(BaseModel):
    name: str = Field(..., max_length=255)
    formula: str = Field(..., max_length=255)
    synonyms: List[str] = Field(default_factory=list)


class LocalChemCreate(LocalChemBase):
    pass


class LocalChemOut(LocalChemBase):
    pass
