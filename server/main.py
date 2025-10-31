
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

import asyncio

# ===========================
# Basic Config
# ===========================
DATABASE_URL = "sqlite:///./reagents.db"

# Allowed origins for CORS (edit to match your deployment)
ALLOWED_ORIGINS = [
    "https://reagent-ology.netlify.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# ===========================
# DB Setup
# ===========================
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Reagent(Base):
    __tablename__ = "reagents"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    tag_uid = Column(String, nullable=False, unique=True, index=True)
    density_g_per_ml = Column(Float, nullable=True)   # None이면 g 기준만
    tare_g = Column(Float, nullable=False, default=0.0)
    unit = Column(String, nullable=False, default="g")  # 기본 표시 단위 ("g" or "ml")
    current_net_g = Column(Float, nullable=False, default=0.0)
    logs = relationship("UsageLog", back_populates="reagent", order_by="desc(UsageLog.ts)")

class UsageLog(Base):
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True)
    reagent_id = Column(Integer, ForeignKey("reagents.id"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    gross_g = Column(Float, nullable=False)
    net_g = Column(Float, nullable=False)
    delta_g = Column(Float, nullable=False)
    delta_ml = Column(Float, nullable=True)
    source = Column(String, nullable=False, default="RS232")
    note = Column(String, nullable=True)
    reagent = relationship("Reagent", back_populates="logs")

class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"

class MeasureJob(Base):
    __tablename__ = "measure_queue"
    id = Column(Integer, primary_key=True)
    tag_uid = Column(String, nullable=False, index=True)
    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.pending)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    claimed_by = Column(String, nullable=True)   # 에이전트 식별자
    result_log_id = Column(Integer, nullable=True)

Base.metadata.create_all(engine)

# ===========================
# FastAPI App
# ===========================
app = FastAPI(title="Reagent API - NFC x Scale")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================
# Pydantic DTOs
# ===========================
class UpsertReagent(BaseModel):
    name: str
    tag_uid: str
    density_g_per_ml: Optional[float] = None
    tare_g: float = 0.0
    unit: str = "g"  # "g" 또는 "ml"
    current_net_g: float = 0.0

class ReagentOut(BaseModel):
    id: int
    name: str
    tag_uid: str
    density_g_per_ml: Optional[float]
    tare_g: float
    unit: str
    current_net_g: float
    current_ml: Optional[float]

    @staticmethod
    def from_model(r: Reagent) -> "ReagentOut":
        ml = (r.current_net_g / r.density_g_per_ml) if r.density_g_per_ml else None
        return ReagentOut(
            id=r.id, name=r.name, tag_uid=r.tag_uid, density_g_per_ml=r.density_g_per_ml,
            tare_g=r.tare_g, unit=r.unit, current_net_g=r.current_net_g, current_ml=ml
        )

class MeasureIn(BaseModel):
    tag_uid: str
    gross_weight_g: float  # ✅ g 단위만 사용 (kg 불필요)
    source: str = "RS232"
    note: Optional[str] = None

class QueueIn(BaseModel):
    tag_uid: str

# ===========================
# SSE (Server-Sent Events)
# ===========================
subscribers: Dict[str, set] = {}  # tag_uid -> set of asyncio.Queue

@app.get("/api/sse/{tag_uid}")
async def sse_tag(tag_uid: str, request: Request):
    q: asyncio.Queue = asyncio.Queue()
    subs = subscribers.setdefault(tag_uid, set())
    subs.add(q)

    async def event_stream():
        try:
            # 최초 핑
            yield "event: ping\ndata: ok\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # keepalive
                    yield "event: ping\ndata: keepalive\n\n"
        finally:
            subs.remove(q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

def notify_tag_update(tag_uid: str, payload: Dict[str, Any]):
    """해당 tag_uid를 구독 중인 클라이언트에 알림"""
    import json
    queues = subscribers.get(tag_uid, set())
    for q in list(queues):
        try:
            q.put_nowait(json.dumps(payload))
        except Exception:
            pass

# ===========================
# Routes - Reagents
# ===========================
@app.post("/api/reagents/upsert")
def upsert_reagent(payload: UpsertReagent):
    db = SessionLocal()
    try:
        r = db.query(Reagent).filter_by(tag_uid=payload.tag_uid).first()
        if not r:
            r = Reagent(**payload.model_dump())
            db.add(r)
        else:
            for k, v in payload.model_dump().items():
                setattr(r, k, v)
        db.commit()
        db.refresh(r)
        return {"ok": True, "reagent": ReagentOut.from_model(r)}
    finally:
        db.close()

@app.get("/api/reagents/by-tag/{tag_uid}", response_model=ReagentOut)
def get_reagent_by_tag(tag_uid: str):
    db = SessionLocal()
    try:
        r = db.query(Reagent).filter_by(tag_uid=tag_uid).first()
        if not r:
            raise HTTPException(404, "Reagent not found")
        return ReagentOut.from_model(r)
    finally:
        db.close()

@app.get("/api/reagents/{rid}", response_model=ReagentOut)
def get_reagent(rid: int):
    db = SessionLocal()
    try:
        r = db.query(Reagent).get(rid)
        if not r:
            raise HTTPException(404, "Reagent not found")
        return ReagentOut.from_model(r)
    finally:
        db.close()

@app.get("/api/reagents/{rid}/logs")
def get_logs(rid: int, limit: int = 50):
    db = SessionLocal()
    try:
        logs = db.query(UsageLog).filter_by(reagent_id=rid).order_by(UsageLog.ts.desc()).limit(limit).all()
        return [
            {
                "ts": l.ts.isoformat(),
                "gross_g": l.gross_g,
                "net_g": l.net_g,
                "delta_g": l.delta_g,
                "delta_ml": l.delta_ml,
                "source": l.source,
                "note": l.note,
            }
            for l in logs
        ]
    finally:
        db.close()

# ===========================
# Routes - Measurement
# ===========================
@app.post("/api/measure")
def measure(payload: MeasureIn):
    db = SessionLocal()
    try:
        r = db.query(Reagent).filter_by(tag_uid=payload.tag_uid).first()
        if not r:
            raise HTTPException(404, "Unknown tag_uid")

        gross = payload.gross_weight_g  # g 단위 입력
        net = max(gross - r.tare_g, 0.0)

        delta_g = net - r.current_net_g
        delta_ml = (delta_g / r.density_g_per_ml) if (r.density_g_per_ml and r.density_g_per_ml > 0) else None

        r.current_net_g = net
        log = UsageLog(
            reagent_id=r.id, gross_g=gross, net_g=net,
            delta_g=delta_g, delta_ml=delta_ml, source=payload.source, note=payload.note
        )
        db.add(log)
        db.commit()

        # SSE 알림 (실패해도 무시)
        try:
            notify_tag_update(r.tag_uid, {"updated": True, "reagent": ReagentOut.from_model(r).model_dump()})
        except Exception:
            pass

        return {
            "ok": True,
            "reagent": ReagentOut.from_model(r),
            "log": {
                "ts": log.ts.isoformat(), "gross_g": gross, "net_g": net,
                "delta_g": delta_g, "delta_ml": delta_ml, "source": log.source, "note": log.note
            }
        }
    finally:
        db.close()

# ===========================
# Routes - Queue
# ===========================
@app.post("/api/queue")
def enqueue_measure(payload: QueueIn):
    db = SessionLocal()
    try:
        # 존재하는 시약인지 확인
        r = db.query(Reagent).filter_by(tag_uid=payload.tag_uid).first()
        if not r:
            raise HTTPException(404, "Unknown tag_uid")
        job = MeasureJob(tag_uid=payload.tag_uid, status=JobStatus.pending)
        db.add(job)
        db.commit()
        db.refresh(job)
        return {"ok": True, "job_id": job.id}
    finally:
        db.close()

@app.post("/api/queue/next")
def claim_next_job(agent: str = "default"):
    db = SessionLocal()
    try:
        job = (db.query(MeasureJob)
                 .filter(MeasureJob.status==JobStatus.pending)
                 .order_by(MeasureJob.created_at.asc())
                 .first())
        if not job:
            return {"ok": True, "job": None}
        job.status = JobStatus.processing
        job.claimed_by = agent
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return {"ok": True, "job": {"id": job.id, "tag_uid": job.tag_uid}}
    finally:
        db.close()

@app.post("/api/queue/{job_id}/done")
def finish_job(job_id: int, log_id: int | None = None):
    db = SessionLocal()
    try:
        job = db.query(MeasureJob).get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        job.status = JobStatus.done
        job.result_log_id = log_id
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
