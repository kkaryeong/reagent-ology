"""FastAPI application with CSV-based storage (NO SQL).

Simplified version for high school project - easy to understand and maintain.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query, status, Response, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from . import schemas, csvdb, localdb
from .localdb import search_local
from .utils import slugify
import re

PUBCHEM_AUTOCOMPLETE_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound/name/{query}/json"
)
PUBCHEM_PROPERTY_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/"
    "MolecularFormula,CID/JSON"
)

app = FastAPI(title="Reagent-ology API (CSV)", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files (serve UI over HTTP so phones can access via LAN IP/mDNS) ---
import os
from pathlib import Path

_here = Path(__file__).resolve().parent
_root = _here.parent  # project root where reagent_ology.html lives

# Mount static files at '/'. API remains under '/api/*'
app.mount(
    "/_ui",
    StaticFiles(directory=str(_root), html=True),
    name="static",
)

@app.get("/")
def root_redirect():
    # Redirect to main UI file for convenience
    return RedirectResponse(url="/reagent_ology.html")

@app.get("/reagent_ology.html")
def serve_ui_file():
    ui_path = _root / "reagent_ology.html"
    if not ui_path.exists():
        # Fallback: redirect to mounted static index if any
        return RedirectResponse(url="/_ui/reagent_ology.html")
    return FileResponse(str(ui_path))


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Lightweight health check for launcher/browser readiness."""
    return {"status": "ok"}


def ensure_unique_slug(base: str, current_id: Optional[int] = None) -> str:
    """Generate unique slug"""
    slug = base or "reagent"
    candidate = slug
    suffix = 1
    
    all_reagents = csvdb.list_all_reagents()
    
    while True:
        conflict = False
        for r in all_reagents:
            if r["slug"] == candidate and (current_id is None or r["id"] != current_id):
                conflict = True
                break
        
        if not conflict:
            return candidate
        
        candidate = f"{slug}-{suffix}"
        suffix += 1


def normalize_optional_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_nfc_tag(value: Optional[str]) -> Optional[str]:
    """Normalize NFC UID by removing separators and uppercasing.
    Examples:
    '04:E4:B4:C2:43:20:90' -> '04E4B4C2432090'
    '04e4b4c2432090' -> '04E4B4C2432090'
    Returns None if input is falsy after stripping.
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    # keep hex digits only
    s = re.sub(r"[^0-9A-Fa-f]", "", s)
    return s.upper() or None


async def fetch_pubchem_suggestions(query: str, limit: int = 8) -> List[Dict[str, Optional[str]]]:
    if not query:
        return []
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(
                PUBCHEM_AUTOCOMPLETE_URL.format(query=quote(query)),
                params={"limit": limit},
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return []

        data = response.json()
        names = data.get("dictionary_terms", {}).get("compound", [])[:limit]
        if not names:
            return []

        tasks = [
            client.get(PUBCHEM_PROPERTY_URL.format(name=quote(name)))
            for name in names
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        suggestions: List[Dict[str, Optional[str]]] = []
        for name, result in zip(names, results):
            formula: Optional[str] = None
            cid: Optional[int] = None
            if isinstance(result, httpx.Response) and result.status_code == 200:
                try:
                    payload = result.json()
                    props = payload.get("PropertyTable", {}).get("Properties", [])
                    if props:
                        record = props[0]
                        formula = record.get("MolecularFormula")
                        cid = record.get("CID")
                except (ValueError, json.JSONDecodeError):
                    formula = None
            suggestions.append({"name": name, "formula": formula, "cid": cid})
        return suggestions


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "storage": "CSV"}


@app.get("/api/reagents", response_model=List[schemas.ReagentOut])
def list_reagents() -> List[schemas.ReagentOut]:
    """모든 시약 목록"""
    reagents = csvdb.list_all_reagents()
    return [schemas.ReagentOut(**r) for r in reagents]


@app.get("/api/reagents/by-nfc/{tag}", response_model=schemas.ReagentOut)
def get_reagent_by_nfc(tag: str) -> schemas.ReagentOut:
    """NFC 태그 UID로 시약 조회"""
    if tag is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag is required")
    cleaned = tag.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag is empty")
    norm_in = normalize_nfc_tag(cleaned)
    for r in csvdb.list_all_reagents():
        stored = r.get("nfc_tag_uid") or ""
        if stored.strip() == cleaned:
            return schemas.ReagentOut(**r)
        if normalize_nfc_tag(stored) == norm_in and norm_in:
            return schemas.ReagentOut(**r)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found for provided NFC tag")


@app.post(
    "/api/reagents",
    response_model=schemas.ReagentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_reagent(payload: schemas.ReagentCreate) -> schemas.ReagentOut:
    """새 시약 등록"""
    base_slug = slugify(payload.name, payload.cas)
    slug = ensure_unique_slug(base_slug)

    volume_ml = payload.volume_ml
    if volume_ml is None and payload.density and (payload.state == 'liquid'):
        volume_ml = payload.quantity / payload.density

    data = {
        "slug": slug,
        "name": payload.name,
        "formula": payload.formula,
        "cas": payload.cas,
        "location": payload.location,
        "storage": payload.storage,
    "state": payload.state,
        "expiry": payload.expiry.isoformat() if payload.expiry else None,
        "hazard": payload.hazard,
        "ghs": payload.ghs,
        "disposal": payload.disposal,
        "density": payload.density,
        "volume_ml": volume_ml,
        "nfc_tag_uid": normalize_optional_string(payload.nfc_tag_uid),
        "quantity": payload.quantity,
        "used": payload.used,
        "discarded": payload.discarded,
    }

    reagent = csvdb.create_reagent(data)
    return schemas.ReagentOut(**reagent)


@app.get("/api/reagents/{identifier}", response_model=schemas.ReagentOut)
def get_reagent(identifier: str) -> schemas.ReagentOut:
    """시약 상세 조회"""
    reagent = csvdb.get_reagent(identifier)
    if not reagent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    return schemas.ReagentOut(**reagent)


@app.put("/api/reagents/{identifier}", response_model=schemas.ReagentOut)
def update_reagent(
    identifier: str,
    payload: schemas.ReagentUpdate,
) -> schemas.ReagentOut:
    """시약 정보 수정"""
    reagent = csvdb.get_reagent(identifier)
    if not reagent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")

    update_data = {}
    
    if payload.name is not None:
        update_data["name"] = payload.name
    if payload.formula is not None:
        update_data["formula"] = payload.formula
    if payload.cas is not None:
        update_data["cas"] = payload.cas
    if payload.location is not None:
        update_data["location"] = payload.location
    if payload.storage is not None:
        update_data["storage"] = payload.storage
    if payload.state is not None:
        update_data["state"] = payload.state
    if payload.expiry is not None:
        update_data["expiry"] = payload.expiry.isoformat() if payload.expiry else None
    if payload.hazard is not None:
        update_data["hazard"] = payload.hazard
    if payload.ghs is not None:
        update_data["ghs"] = payload.ghs
    if payload.disposal is not None:
        update_data["disposal"] = payload.disposal
    
    # 밀도 업데이트 시 부피 재계산 (액체에 한함)
    if payload.density is not None:
        update_data["density"] = payload.density
        effective_state = payload.state if payload.state is not None else reagent.get("state")
        if payload.density and reagent["quantity"] is not None and effective_state == 'liquid':
            update_data["volume_ml"] = reagent["quantity"] / payload.density
    
    if payload.volume_ml is not None:
        update_data["volume_ml"] = payload.volume_ml
        # 부피를 직접 지정하면 액체로 간주될 수 있으나, 안전하게 density가 있을 때만 역산
        if reagent["density"] and payload.quantity is None:
            update_data["quantity"] = payload.volume_ml * reagent["density"]
    
    if payload.nfc_tag_uid is not None:
        update_data["nfc_tag_uid"] = normalize_optional_string(payload.nfc_tag_uid)
    
    # 수량 업데이트 시 부피 재계산 (액체에 한함)
    if payload.quantity is not None:
        update_data["quantity"] = payload.quantity
        effective_state = payload.state if payload.state is not None else reagent.get("state")
        if reagent["density"] and effective_state == 'liquid':
            update_data["volume_ml"] = payload.quantity / reagent["density"]
    
    if payload.used is not None:
        update_data["used"] = payload.used
    if payload.discarded is not None:
        update_data["discarded"] = payload.discarded

    # slug 업데이트 체크
    if payload.name is not None or payload.cas is not None:
        new_slug = slugify(
            payload.name if payload.name is not None else reagent["name"],
            payload.cas if payload.cas is not None else reagent["cas"]
        )
        update_data["slug"] = ensure_unique_slug(new_slug, current_id=reagent["id"])

    updated = csvdb.update_reagent(identifier, update_data)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")
    
    return schemas.ReagentOut(**updated)


@app.delete(
    "/api/reagents/{identifier}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_reagent(identifier: str) -> Response:
    """시약 삭제"""
    success = csvdb.delete_reagent(identifier)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/reagents/{identifier}/use", response_model=schemas.ReagentOut)
def use_reagent(
    identifier: str,
    payload: schemas.UseRequest,
) -> schemas.ReagentOut:
    """시약 사용"""
    reagent = csvdb.get_reagent(identifier)
    if not reagent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    
    if reagent["quantity"] < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient quantity")
    
    prev = reagent["quantity"]
    new_qty = max(0.0, reagent["quantity"] - payload.amount)
    
    # 사용량 기록
    csvdb.add_usage_log(
        reagent_id=reagent["id"],
        prev_qty=prev,
        new_qty=new_qty,
        delta=-payload.amount,
        source="use",
        note=payload.note,
    )
    
    # 시약 정보 업데이트
    update_data = {
        "quantity": new_qty,
        "used": reagent["used"] + payload.amount,
    }
    
    # 액체이고 밀도가 있으면 부피도 업데이트
    if reagent.get("state") == 'liquid' and reagent["density"]:
        update_data["volume_ml"] = new_qty / reagent["density"]
    
    updated = csvdb.update_reagent(identifier, update_data)
    return schemas.ReagentOut(**updated)


@app.post("/api/reagents/{identifier}/discard", response_model=schemas.ReagentOut)
def discard_reagent(
    identifier: str,
    payload: schemas.UseRequest,
) -> schemas.ReagentOut:
    """시약 폐기"""
    reagent = csvdb.get_reagent(identifier)
    if not reagent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    
    if reagent["quantity"] < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient quantity")
    
    prev = reagent["quantity"]
    new_qty = max(0.0, reagent["quantity"] - payload.amount)
    
    # 폐기량 기록
    csvdb.add_usage_log(
        reagent_id=reagent["id"],
        prev_qty=prev,
        new_qty=new_qty,
        delta=-payload.amount,
        source="discard",
        note=payload.note,
    )
    
    # 시약 정보 업데이트
    update_data = {
        "quantity": new_qty,
        "discarded": reagent["discarded"] + payload.amount,
    }
    
    # 액체이고 밀도가 있으면 부피도 업데이트
    if reagent.get("state") == 'liquid' and reagent["density"]:
        update_data["volume_ml"] = new_qty / reagent["density"]
    
    updated = csvdb.update_reagent(identifier, update_data)
    return schemas.ReagentOut(**updated)


@app.post("/api/reagents/{identifier}/measurement", response_model=schemas.ReagentOut)
def update_measurement(
    identifier: str,
    payload: schemas.MeasurementRequest,
) -> schemas.ReagentOut:
    """저울 측정값 업데이트"""
    reagent = csvdb.get_reagent(identifier)
    if not reagent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    
    mass = payload.measured_mass
    if mass is None:
        mass = payload.new_quantity
    volume = payload.measured_volume
    
    if mass is None and volume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide measured_mass or measured_volume",
        )
    
    prev_mass = reagent["quantity"] or 0.0
    
    # 질량/부피 계산
    if mass is None and volume is not None:
        if reagent["density"]:
            mass = volume * reagent["density"]
        else:
            mass = volume
    
    if volume is None and mass is not None:
        if reagent.get("state") == 'liquid' and reagent["density"]:
            volume = mass / reagent["density"]
    
    delta = (mass or 0.0) - prev_mass
    
    # 사용 기록 추가
    csvdb.add_usage_log(
        reagent_id=reagent["id"],
        prev_qty=prev_mass,
        new_qty=mass or 0.0,
        delta=delta,
        source=payload.source,
        note=payload.note,
    )
    
    # 시약 정보 업데이트
    update_data = {
        "quantity": mass,
        "volume_ml": volume,
    }
    
    updated = csvdb.update_reagent(identifier, update_data)
    return schemas.ReagentOut(**updated)


@app.post("/api/measurements/weight", response_model=schemas.ReagentOut)
def record_weight_measurement(
    payload: schemas.WeightMeasurementRequest,
) -> schemas.ReagentOut:
    """NFC 태그로 시약 찾아서 저울 측정값 기록"""
    tag = payload.nfc_tag_uid.strip()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NFC tag UID cannot be empty",
        )
    
    # NFC 태그로 시약 찾기
    all_reagents = csvdb.list_all_reagents()
    reagent = None
    norm_in = normalize_nfc_tag(tag)
    for r in all_reagents:
        stored = r.get("nfc_tag_uid") or ""
        if stored == tag:
            reagent = r
            break
        if norm_in and normalize_nfc_tag(stored) == norm_in:
            reagent = r
            break
    
    if not reagent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reagent not found for provided NFC tag",
        )
    
    # 측정값 업데이트
    prev_mass = reagent["quantity"] or 0.0
    mass = payload.measured_mass
    volume = None
    
    if reagent.get("state") == 'liquid' and reagent["density"]:
        volume = mass / reagent["density"]
    
    delta = mass - prev_mass
    
    # 사용 기록 추가
    csvdb.add_usage_log(
        reagent_id=reagent["id"],
        prev_qty=prev_mass,
        new_qty=mass,
        delta=delta,
        source=payload.source,
        note=payload.note,
    )
    
    # 시약 정보 업데이트
    update_data = {
        "quantity": mass,
        "volume_ml": volume,
    }
    
    updated = csvdb.update_reagent(str(reagent["id"]), update_data)
    return schemas.ReagentOut(**updated)


@app.get(
    "/api/reagents/{identifier}/usage",
    response_model=List[schemas.UsageLogOut],
)
def list_usage(identifier: str) -> List[schemas.UsageLogOut]:
    """시약 사용 이력 조회"""
    reagent = csvdb.get_reagent(identifier)
    if not reagent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    
    logs = csvdb.get_usage_logs(reagent["id"])
    return [schemas.UsageLogOut(**log) for log in logs]


@app.post("/api/reagents/reset-stats")
def reset_stats() -> Dict[str, str]:
    """모든 시약의 사용/폐기 통계 초기화"""
    csvdb.reset_all_stats()
    return {"status": "ok"}


@app.get(
    "/api/autocomplete",
    response_model=schemas.AutocompleteResponse,
)
async def autocomplete(
    q: str = Query(..., min_length=2, max_length=60),
    limit: int = Query(8, ge=1, le=20),
) -> schemas.AutocompleteResponse:
    """자동완성: 로컬 CSV 우선, 부족하면 PubChem"""
    # 1) 로컬 우선
    local = search_local(q, limit=limit)
    seen = {item["name"] for item in local}
    results: List[Dict[str, Optional[str]]] = list(local)

    # 2) 부족하면 PubChem으로 보강
    remaining = max(0, limit - len(results))
    if remaining > 0:
        remote = await fetch_pubchem_suggestions(q, limit=limit * 2)
        for item in remote:
            name = item.get("name")
            if not name or name in seen:
                continue
            results.append(item)
            seen.add(name)
            if len(results) >= limit:
                break

    return schemas.AutocompleteResponse(suggestions=results)


@app.get(
    "/api/autocomplete/local",
    response_model=schemas.AutocompleteResponse,
)
async def autocomplete_local(
    q: str = Query(..., min_length=1, max_length=60),
    limit: int = Query(8, ge=1, le=50),
) -> schemas.AutocompleteResponse:
    """로컬 CSV만 검색"""
    return schemas.AutocompleteResponse(suggestions=search_local(q, limit=limit))


# Local autocomplete DB CRUD endpoints
@app.get("/api/autocomplete/local-db", response_model=List[schemas.LocalChemOut])
def list_local_db() -> List[schemas.LocalChemOut]:
    """자동완성 DB 전체 목록"""
    return [schemas.LocalChemOut(**item) for item in localdb.list_all()]


@app.post("/api/autocomplete/local-db", response_model=schemas.LocalChemOut, status_code=201)
def add_local_db(payload: schemas.LocalChemCreate) -> schemas.LocalChemOut:
    """자동완성 DB 항목 추가"""
    try:
        item = localdb.add_item(
            payload.name,
            payload.formula,
            payload.synonyms,
            cas=payload.cas,
            storage=payload.storage,
            ghs=payload.ghs,
            disposal=payload.disposal,
            density=payload.density,
        )
        return schemas.LocalChemOut(**item)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Item with the same name already exists")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/autocomplete/local-db/{name}", status_code=204, response_class=Response)
def delete_local_db(name: str) -> Response:
    """자동완성 DB 항목 삭제"""
    try:
        localdb.delete_item(name)
        return Response(status_code=204)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")


@app.put("/api/autocomplete/local-db/{name}", response_model=schemas.LocalChemOut)
def update_local_db(name: str, payload: schemas.LocalChemCreate) -> schemas.LocalChemOut:
    """자동완성 DB 항목 수정"""
    try:
        item = localdb.update_item(
            name,
            name=payload.name,
            formula=payload.formula,
            synonyms=payload.synonyms,
            cas=payload.cas,
            storage=payload.storage,
            ghs=payload.ghs,
            disposal=payload.disposal,
            density=payload.density,
        )
        return schemas.LocalChemOut(**item)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Item with the same name already exists")


@app.get("/api/locations", response_model=List[str])
def list_locations(
    q: Optional[str] = Query(None, min_length=1, max_length=60),
) -> List[str]:
    """등록된 시약의 location 목록 (자동완성용)"""
    all_reagents = csvdb.list_all_reagents()
    locations = set()
    
    for r in all_reagents:
        loc = r.get("location")
        if loc and isinstance(loc, str):
            loc = loc.strip()
            if loc:
                locations.add(loc)
    
    # 쿼리가 있으면 필터링
    if q:
        q_lower = q.lower()
        locations = {loc for loc in locations if q_lower in loc.lower()}
    
    # 알파벳 순 정렬
    return sorted(locations)


# ============= Scale Integration Endpoints =============

@app.get("/api/scale/ports")
def list_scale_ports():
    """사용 가능한 시리얼 포트 목록 조회"""
    from .scale_reader import detect_scales
    
    try:
        ports = detect_scales()
        return {"ports": ports}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list ports: {str(e)}"
        )


@app.get("/api/scale/weight")
def read_scale_weight(
    port: Optional[str] = Query(None, description="Serial port name"),
    baudrate: int = Query(9600, description="Baudrate for serial communication"),
):
    """저울에서 현재 무게 읽기 (3초 안정화)"""
    from .scale_reader import ScaleReader
    
    try:
        scale = ScaleReader(port=port, baudrate=baudrate)
        if not scale.connect():
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to scale"
            )
        
        try:
            # 3초 동안 무게가 안정될 때까지 대기
            weight = scale.get_stable_weight(max_attempts=30, tolerance=0.1, stable_duration=3.0)
            if weight is None:
                raise HTTPException(
                    status_code=503,
                    detail="Could not get stable weight reading (waited for 3 seconds stability)"
                )
            
            return {
                "weight_grams": weight,
                "port": scale.port,
                "timestamp": datetime.now().isoformat()
            }
        finally:
            scale.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading scale: {str(e)}"
        )


@app.post("/api/reagents/{reagent_id}/measure-weight")
def update_reagent_weight_from_scale(
    reagent_id: int,
    port: Optional[str] = Query(None, description="Serial port name"),
    baudrate: int = Query(9600, description="Baudrate"),
    note: Optional[str] = Query(None, description="Optional note"),
):
    """저울에서 무게를 읽어 시약의 quantity 업데이트 (3초 안정화)"""
    from .scale_reader import ScaleReader
    
    # 시약 조회
    # csvdb.get_reagent은 문자열 identifier를 받아 숫자도 처리합니다.
    reagent = csvdb.get_reagent(str(reagent_id))
    if not reagent:
        raise HTTPException(status_code=404, detail="Reagent not found")
    
    # 저울에서 무게 읽기
    try:
        scale = ScaleReader(port=port, baudrate=baudrate)
        if not scale.connect():
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to scale"
            )
        
        try:
            # 3초 동안 무게가 안정될 때까지 대기
            weight = scale.get_stable_weight(max_attempts=30, tolerance=0.1, stable_duration=3.0)
            if weight is None:
                raise HTTPException(
                    status_code=503,
                    detail="Could not get stable weight reading (waited for 3 seconds stability)"
                )
        finally:
            scale.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading scale: {str(e)}"
        )
    
    # 이전 수량 저장
    prev_qty = reagent["quantity"]
    
    # 수량 업데이트
    updated = csvdb.update_reagent(
        str(reagent_id),
        {"quantity": weight},
    )
    
    # 사용 로그 기록
    delta = weight - prev_qty
    csvdb.add_usage_log(
        reagent_id=reagent_id,
        prev_qty=prev_qty,
        new_qty=weight,
        delta=delta,
        source="scale",
        note=note or f"Weight measured from scale: {weight}g",
    )
    
    return {
        "reagent": schemas.ReagentOut(**updated),
        "measured_weight": weight,
        "previous_quantity": prev_qty,
        "delta": delta,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/scale/tare")
def tare_scale(
    port: Optional[str] = Query(None, description="Serial port name"),
    baudrate: int = Query(9600, description="Baudrate"),
):
    """저울 영점 조정 (Tare)"""
    from .scale_reader import ScaleReader
    
    try:
        scale = ScaleReader(port=port, baudrate=baudrate)
        if not scale.connect():
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to scale"
            )
        
        try:
            success = scale.tare()
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to send tare command"
                )
            
            return {
                "success": True,
                "message": "Scale tared successfully",
                "timestamp": datetime.now().isoformat()
            }
        finally:
            scale.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error taring scale: {str(e)}"
        )


# ============= Scale Measurement CSV Upload Endpoints =============

@app.post("/api/scale/upload-measurements")
async def upload_scale_measurements(file: UploadFile = File(...)):
    """저울 측정값 CSV 파일을 업로드하여 시약 수량 일괄 업데이트
    
    CSV 형식:
    nfc_tag_uid,reagent_id,reagent_name,measured_weight,timestamp,note,operator
    
    최소 하나의 식별자(nfc_tag_uid, reagent_id, reagent_name)가 필요
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="CSV 파일만 업로드 가능합니다"
        )
    
    try:
        # CSV 파일 읽기
        contents = await file.read()
        csv_text = contents.decode('utf-8-sig')  # BOM 제거
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": [],
            "updates": []
        }
        
        for row_num, row in enumerate(csv_reader, start=2):  # 헤더 다음부터
            results["total"] += 1
            
            try:
                # 측정 무게 파싱
                measured_weight_str = row.get('measured_weight', '').strip()
                if not measured_weight_str:
                    raise ValueError("measured_weight 필드가 비어있습니다")
                
                measured_weight = float(measured_weight_str)
                if measured_weight < 0:
                    raise ValueError("무게는 0 이상이어야 합니다")
                
                # 시약 찾기 (nfc_tag_uid, reagent_id, reagent_name 순서로 시도)
                reagent = None
                identifier = None
                
                # 1. NFC 태그 UID로 찾기
                nfc_tag_uid = row.get('nfc_tag_uid', '').strip()
                if nfc_tag_uid:
                    all_reagents = csvdb.list_all_reagents()
                    norm_in = normalize_nfc_tag(nfc_tag_uid)
                    for r in all_reagents:
                        stored = r.get('nfc_tag_uid') or ''
                        if stored == nfc_tag_uid:
                            reagent = r
                            identifier = f"NFC:{nfc_tag_uid}"
                            break
                        if norm_in and normalize_nfc_tag(stored) == norm_in:
                            reagent = r
                            identifier = f"NFC:{nfc_tag_uid}"
                            break
                
                # 2. reagent_id로 찾기
                if not reagent:
                    reagent_id_str = row.get('reagent_id', '').strip()
                    if reagent_id_str:
                        reagent_id = int(reagent_id_str)
                        reagent = csvdb.get_reagent(str(reagent_id))
                        if reagent:
                            identifier = f"ID:{reagent_id}"
                
                # 3. reagent_name으로 찾기
                if not reagent:
                    reagent_name = row.get('reagent_name', '').strip()
                    if reagent_name:
                        all_reagents = csvdb.list_all_reagents()
                        for r in all_reagents:
                            if r.get('name', '').strip() == reagent_name:
                                reagent = r
                                identifier = f"Name:{reagent_name}"
                                break
                
                if not reagent:
                    raise ValueError(
                        "시약을 찾을 수 없습니다. nfc_tag_uid, reagent_id, reagent_name 중 하나를 확인하세요"
                    )
                
                # 이전 수량 저장
                prev_qty = reagent["quantity"]
                
                # 시약 수량 업데이트
                updated = csvdb.update_reagent(
                    str(reagent["id"]),
                    {"quantity": measured_weight},
                )
                
                # 사용 로그 기록
                delta = measured_weight - prev_qty
                note = row.get('note', '').strip()
                operator = row.get('operator', '').strip()
                timestamp_str = row.get('timestamp', '').strip()
                
                log_note = f"CSV 업로드: {note}" if note else "CSV 업로드"
                if operator:
                    log_note += f" (측정자: {operator})"
                if timestamp_str:
                    log_note += f" [시간: {timestamp_str}]"
                
                csvdb.add_usage_log(
                    reagent_id=reagent["id"],
                    prev_qty=prev_qty,
                    new_qty=measured_weight,
                    delta=delta,
                    source="csv_upload",
                    note=log_note,
                )
                
                results["success"] += 1
                results["updates"].append({
                    "row": row_num,
                    "identifier": identifier,
                    "reagent_name": reagent["name"],
                    "previous_quantity": prev_qty,
                    "new_quantity": measured_weight,
                    "delta": delta
                })
                
            except ValueError as e:
                results["failed"] += 1
                results["errors"].append({
                    "row": row_num,
                    "error": str(e),
                    "data": dict(row)
                })
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "row": row_num,
                    "error": f"처리 중 오류: {str(e)}",
                    "data": dict(row)
                })
        
        return {
            "message": f"CSV 파일 처리 완료: {results['success']}건 성공, {results['failed']}건 실패",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="CSV 파일 인코딩 오류. UTF-8 인코딩을 사용해주세요"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"CSV 파일 처리 중 오류: {str(e)}"
        )


@app.post("/api/scale/save-measurement")
async def save_scale_measurement_to_csv(
    nfc_tag_uid: Optional[str] = None,
    reagent_id: Optional[int] = None,
    reagent_name: Optional[str] = None,
    measured_weight: float = Query(..., ge=0),
    note: Optional[str] = None,
    operator: Optional[str] = None,
):
    """저울 측정값을 CSV 파일에 저장 (data/scale_measurements.csv)
    
    이 엔드포인트는 측정값을 즉시 DB에 반영하지 않고 CSV 파일에만 저장합니다.
    나중에 /api/scale/upload-measurements로 일괄 업로드할 수 있습니다.
    """
    import os
    from pathlib import Path
    
    # CSV 파일 경로
    csv_file = Path(__file__).parent.parent / "data" / "scale_measurements.csv"
    
    # 파일이 없으면 헤더와 함께 생성
    file_exists = csv_file.exists()
    
    try:
        with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 헤더 작성 (파일이 없을 때만)
            if not file_exists:
                writer.writerow([
                    'nfc_tag_uid', 'reagent_id', 'reagent_name', 
                    'measured_weight', 'timestamp', 'note', 'operator'
                ])
            
            # 데이터 작성
            writer.writerow([
                nfc_tag_uid or '',
                reagent_id or '',
                reagent_name or '',
                measured_weight,
                datetime.now().isoformat(),
                note or '',
                operator or ''
            ])
        
        return {
            "success": True,
            "message": "측정값이 CSV 파일에 저장되었습니다",
            "file": str(csv_file),
            "data": {
                "nfc_tag_uid": nfc_tag_uid,
                "reagent_id": reagent_id,
                "reagent_name": reagent_name,
                "measured_weight": measured_weight,
                "timestamp": datetime.now().isoformat(),
                "note": note,
                "operator": operator
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"CSV 파일 저장 중 오류: {str(e)}"
        )
