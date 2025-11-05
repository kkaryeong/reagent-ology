"""CSV-based reagent inventory database with usage log tracking.

High school project version - simple CSV storage without SQL complexity.

CSV schemas:
    reagents.csv: id,slug,name,formula,cas,location,storage,state,expiry,hazard,ghs,disposal,density,volume_ml,nfc_tag_uid,scale_device,quantity,used,discarded,created_at,updated_at
    usage_logs.csv: id,reagent_id,prev_qty,new_qty,delta,source,note,created_at
"""
from __future__ import annotations

import csv
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any

from . import localdb


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REAGENTS_CSV = DATA_DIR / "reagents.csv"
USAGE_CSV = DATA_DIR / "usage_logs.csv"
_lock = threading.Lock()


@dataclass
class Reagent:
    """화학 시약 데이터 클래스"""
    id: int
    slug: str
    name: str
    formula: str
    location: str
    quantity: float = 0.0
    cas: Optional[str] = None
    storage: Optional[str] = None
    state: Optional[str] = None  # 'liquid' | 'solid'
    expiry: Optional[str] = None  # ISO format YYYY-MM-DD
    hazard: Optional[str] = None
    ghs: List[str] = field(default_factory=list)
    disposal: Optional[str] = None
    density: Optional[float] = None
    volume_ml: Optional[float] = None
    nfc_tag_uid: Optional[str] = None
    scale_device: Optional[str] = None
    used: float = 0.0
    discarded: float = 0.0
    created_at: Optional[str] = None  # ISO format
    updated_at: Optional[str] = None  # ISO format


@dataclass
class UsageLog:
    """사용 기록 데이터 클래스"""
    id: int
    reagent_id: int
    prev_qty: float
    new_qty: float
    delta: float
    source: str = "manual"
    note: Optional[str] = None
    created_at: Optional[str] = None  # ISO format


def _ensure_data_dir() -> None:
    """데이터 디렉토리 생성"""
    DATA_DIR.mkdir(exist_ok=True)


def _get_next_id(csv_path: Path) -> int:
    """CSV에서 다음 ID 생성"""
    if not csv_path.exists():
        return 1
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ids = [int(row["id"]) for row in reader if row.get("id")]
        return max(ids, default=0) + 1


def _read_reagents() -> List[Reagent]:
    """모든 시약 읽기"""
    _ensure_data_dir()
    if not REAGENTS_CSV.exists():
        return []
    
    items: List[Reagent] = []
    with REAGENTS_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # GHS는 세미콜론으로 구분
            ghs_raw = (row.get("ghs") or "").strip()
            ghs = [s.strip() for s in ghs_raw.split(";") if s.strip()]
            
            # 숫자 필드 처리
            density = float(row["density"]) if row.get("density") and row["density"] != "" else None
            volume_ml = float(row["volume_ml"]) if row.get("volume_ml") and row["volume_ml"] != "" else None
            
            items.append(Reagent(
                id=int(row["id"]),
                slug=row["slug"],
                name=row["name"],
                formula=row["formula"],
                cas=row.get("cas") or None,
                location=row["location"],
                storage=row.get("storage") or None,
                state=row.get("state") or None,
                expiry=row.get("expiry") or None,
                hazard=row.get("hazard") or None,
                ghs=ghs,
                disposal=row.get("disposal") or None,
                density=density,
                volume_ml=volume_ml,
                nfc_tag_uid=row.get("nfc_tag_uid") or None,
                scale_device=row.get("scale_device") or None,
                quantity=float(row["quantity"]),
                used=float(row.get("used") or 0),
                discarded=float(row.get("discarded") or 0),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            ))
    return items


def _write_reagents(items: List[Reagent]) -> None:
    """모든 시약 쓰기"""
    _ensure_data_dir()
    with REAGENTS_CSV.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "id", "slug", "name", "formula", "cas", "location", "storage", "state", "expiry",
            "hazard", "ghs", "disposal", "density", "volume_ml", "nfc_tag_uid",
            "scale_device", "quantity", "used", "discarded", "created_at", "updated_at"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for r in items:
            writer.writerow({
                "id": r.id,
                "slug": r.slug,
                "name": r.name,
                "formula": r.formula,
                "cas": r.cas or "",
                "location": r.location,
                "storage": r.storage or "",
                "state": r.state or "",
                "expiry": r.expiry or "",
                "hazard": r.hazard or "",
                "ghs": ";".join(r.ghs) if r.ghs else "",
                "disposal": r.disposal or "",
                "density": f"{r.density}" if r.density is not None else "",
                "volume_ml": f"{r.volume_ml}" if r.volume_ml is not None else "",
                "nfc_tag_uid": r.nfc_tag_uid or "",
                "scale_device": r.scale_device or "",
                "quantity": r.quantity,
                "used": r.used,
                "discarded": r.discarded,
                "created_at": r.created_at or "",
                "updated_at": r.updated_at or "",
            })


def _read_logs(reagent_id: Optional[int] = None) -> List[UsageLog]:
    """사용 기록 읽기"""
    _ensure_data_dir()
    if not USAGE_CSV.exists():
        return []
    
    logs: List[UsageLog] = []
    with USAGE_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            log = UsageLog(
                id=int(row["id"]),
                reagent_id=int(row["reagent_id"]),
                prev_qty=float(row["prev_qty"]),
                new_qty=float(row["new_qty"]),
                delta=float(row["delta"]),
                source=row.get("source") or "manual",
                note=row.get("note") or None,
                created_at=row.get("created_at"),
            )
            if reagent_id is None or log.reagent_id == reagent_id:
                logs.append(log)
    return logs


def _write_log(log: UsageLog) -> None:
    """사용 기록 추가"""
    _ensure_data_dir()
    file_exists = USAGE_CSV.exists()
    
    with USAGE_CSV.open("a", encoding="utf-8", newline="") as f:
        fieldnames = ["id", "reagent_id", "prev_qty", "new_qty", "delta", "source", "note", "created_at"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            "id": log.id,
            "reagent_id": log.reagent_id,
            "prev_qty": log.prev_qty,
            "new_qty": log.new_qty,
            "delta": log.delta,
            "source": log.source,
            "note": log.note or "",
            "created_at": log.created_at or datetime.utcnow().isoformat(),
        })


# ==================== Public API ====================

def list_all_reagents() -> List[Dict[str, Any]]:
    """모든 시약 목록 반환"""
    with _lock:
        items = _read_reagents()
    return [reagent_to_dict(r) for r in items]


def get_reagent(identifier: str) -> Optional[Dict[str, Any]]:
    """ID 또는 slug로 시약 조회"""
    with _lock:
        items = _read_reagents()
    
    for r in items:
        if identifier.isdigit() and r.id == int(identifier):
            return reagent_to_dict(r)
        if r.slug == identifier:
            return reagent_to_dict(r)
    return None


def create_reagent(data: Dict[str, Any]) -> Dict[str, Any]:
    """새 시약 등록"""
    with _lock:
        items = _read_reagents()
        new_id = _get_next_id(REAGENTS_CSV)
        
        now = datetime.utcnow().isoformat()
        reagent = Reagent(
            id=new_id,
            slug=data["slug"],
            name=data["name"],
            formula=data["formula"],
            cas=data.get("cas"),
            location=data["location"],
            storage=data.get("storage"),
            state=data.get("state"),
            expiry=data.get("expiry"),
            hazard=data.get("hazard"),
            ghs=data.get("ghs", []),
            disposal=data.get("disposal"),
            density=data.get("density"),
            volume_ml=data.get("volume_ml"),
            nfc_tag_uid=data.get("nfc_tag_uid"),
            scale_device=data.get("scale_device"),
            quantity=data.get("quantity", 0.0),
            used=data.get("used", 0.0),
            discarded=data.get("discarded", 0.0),
            created_at=now,
            updated_at=now,
        )
        # 밀도와 질량이 있고, 명시적 volume_ml이 없으면 역산하여 저장
        if (reagent.volume_ml is None) and (reagent.density is not None) and (reagent.density > 0) and (reagent.state == "liquid"):
            try:
                reagent.volume_ml = reagent.quantity / reagent.density
            except Exception:
                # 계산 실패 시 무시 (CSV 저장 형식 유지)
                pass

        items.append(reagent)
        _write_reagents(items)
    
    # 자동완성 DB에도 추가
    localdb.add_or_update_from_reagent(
        name=reagent.name,
        formula=reagent.formula,
        cas=reagent.cas,
        storage=reagent.storage,
        ghs=reagent.ghs,
        disposal=reagent.disposal,
        density=reagent.density,
    )
    
    return reagent_to_dict(reagent)


def update_reagent(identifier: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """시약 정보 수정"""
    with _lock:
        items = _read_reagents()
        idx = None
        
        for i, r in enumerate(items):
            if (identifier.isdigit() and r.id == int(identifier)) or r.slug == identifier:
                idx = i
                break
        
        if idx is None:
            return None
        
        reagent = items[idx]
        
        # 업데이트 가능한 필드만 변경
        changed_quantity = False
        changed_density = False
        if "name" in data:
            reagent.name = data["name"]
        if "formula" in data:
            reagent.formula = data["formula"]
        if "cas" in data:
            reagent.cas = data["cas"]
        if "location" in data:
            reagent.location = data["location"]
        if "storage" in data:
            reagent.storage = data["storage"]
        if "expiry" in data:
            reagent.expiry = data["expiry"]
        if "state" in data:
            reagent.state = data["state"]
        if "hazard" in data:
            reagent.hazard = data["hazard"]
        if "ghs" in data:
            reagent.ghs = data["ghs"]
        if "disposal" in data:
            reagent.disposal = data["disposal"]
        if "density" in data:
            reagent.density = data["density"]
            changed_density = True
        if "volume_ml" in data:
            reagent.volume_ml = data["volume_ml"]
        if "nfc_tag_uid" in data:
            reagent.nfc_tag_uid = data["nfc_tag_uid"]
        if "scale_device" in data:
            reagent.scale_device = data["scale_device"]
        if "quantity" in data:
            reagent.quantity = data["quantity"]
            changed_quantity = True
        if "used" in data:
            reagent.used = data["used"]
        if "discarded" in data:
            reagent.discarded = data["discarded"]
        if "slug" in data:
            reagent.slug = data["slug"]

        # 자동 부피 갱신: quantity 또는 density가 변경되었고, 별도로 volume_ml을 지정하지 않았다면
        if ("volume_ml" not in data) and (changed_quantity or changed_density):
            if (reagent.density is not None) and reagent.density > 0 and (reagent.state == "liquid"):
                try:
                    reagent.volume_ml = reagent.quantity / reagent.density
                except Exception:
                    # 계산 실패 시 기존 값 유지
                    pass
        
        reagent.updated_at = datetime.utcnow().isoformat()
        
        _write_reagents(items)
    
    # 자동완성 DB에도 업데이트
    localdb.add_or_update_from_reagent(
        name=reagent.name,
        formula=reagent.formula,
        cas=reagent.cas,
        storage=reagent.storage,
        ghs=reagent.ghs,
        disposal=reagent.disposal,
        density=reagent.density,
    )
    
    return reagent_to_dict(reagent)


def delete_reagent(identifier: str) -> bool:
    """시약 삭제"""
    with _lock:
        items = _read_reagents()
        new_items = []
        found = False
        
        for r in items:
            if (identifier.isdigit() and r.id == int(identifier)) or r.slug == identifier:
                found = True
            else:
                new_items.append(r)
        
        if found:
            _write_reagents(new_items)
        
        return found


def add_usage_log(reagent_id: int, prev_qty: float, new_qty: float, delta: float,
                  source: str = "manual", note: Optional[str] = None) -> Dict[str, Any]:
    """사용 기록 추가"""
    with _lock:
        log_id = _get_next_id(USAGE_CSV)
        log = UsageLog(
            id=log_id,
            reagent_id=reagent_id,
            prev_qty=prev_qty,
            new_qty=new_qty,
            delta=delta,
            source=source,
            note=note,
            created_at=datetime.utcnow().isoformat(),
        )
        _write_log(log)
    
    return log_to_dict(log)


def get_usage_logs(reagent_id: int) -> List[Dict[str, Any]]:
    """특정 시약의 사용 기록 조회"""
    with _lock:
        logs = _read_logs(reagent_id)
    
    # 최신순 정렬
    logs.sort(key=lambda x: x.created_at or "", reverse=True)
    return [log_to_dict(log) for log in logs]


def reset_all_stats() -> None:
    """모든 시약의 used, discarded 초기화"""
    with _lock:
        items = _read_reagents()
        for r in items:
            r.used = 0.0
            r.discarded = 0.0
            r.updated_at = datetime.utcnow().isoformat()
        _write_reagents(items)


def reagent_to_dict(r: Reagent) -> Dict[str, Any]:
    """Reagent 객체를 딕셔너리로 변환"""
    return {
        "id": r.id,
        "slug": r.slug,
        "name": r.name,
        "formula": r.formula,
        "cas": r.cas,
        "location": r.location,
        "storage": r.storage,
        "state": r.state,
        "expiry": r.expiry,
        "hazard": r.hazard,
        "ghs": r.ghs,
        "disposal": r.disposal,
        "density": r.density,
        "volume_ml": r.volume_ml,
        "nfc_tag_uid": r.nfc_tag_uid,
        "quantity": r.quantity,
        "used": r.used,
        "discarded": r.discarded,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def log_to_dict(log: UsageLog) -> Dict[str, Any]:
    """UsageLog 객체를 딕셔너리로 변환"""
    return {
        "id": log.id,
        "reagent_id": log.reagent_id,
        "prev_qty": log.prev_qty,
        "new_qty": log.new_qty,
        "delta": log.delta,
        "source": log.source,
        "note": log.note,
        "created_at": log.created_at,
    }
