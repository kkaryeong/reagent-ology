"""FastAPI application with CSV-based storage (NO SQL).

Simplified version for high school project - easy to understand and maintain.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query, status, Response
from fastapi.middleware.cors import CORSMiddleware

from . import schemas, csvdb, localdb
from .localdb import search_local
from .utils import slugify

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
    if volume_ml is None and payload.density:
        volume_ml = payload.quantity / payload.density

    data = {
        "slug": slug,
        "name": payload.name,
        "formula": payload.formula,
        "cas": payload.cas,
        "location": payload.location,
        "storage": payload.storage,
        "expiry": payload.expiry.isoformat() if payload.expiry else None,
        "hazard": payload.hazard,
        "ghs": payload.ghs,
        "disposal": payload.disposal,
        "density": payload.density,
        "volume_ml": volume_ml,
        "nfc_tag_uid": normalize_optional_string(payload.nfc_tag_uid),
        "scale_device": normalize_optional_string(payload.scale_device),
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
    if payload.expiry is not None:
        update_data["expiry"] = payload.expiry.isoformat() if payload.expiry else None
    if payload.hazard is not None:
        update_data["hazard"] = payload.hazard
    if payload.ghs is not None:
        update_data["ghs"] = payload.ghs
    if payload.disposal is not None:
        update_data["disposal"] = payload.disposal
    
    # 밀도 업데이트 시 부피 재계산
    if payload.density is not None:
        update_data["density"] = payload.density
        if payload.density and reagent["quantity"] is not None:
            update_data["volume_ml"] = reagent["quantity"] / payload.density
    
    if payload.volume_ml is not None:
        update_data["volume_ml"] = payload.volume_ml
        if reagent["density"] and payload.quantity is None:
            update_data["quantity"] = payload.volume_ml * reagent["density"]
    
    if payload.nfc_tag_uid is not None:
        update_data["nfc_tag_uid"] = normalize_optional_string(payload.nfc_tag_uid)
    if payload.scale_device is not None:
        update_data["scale_device"] = normalize_optional_string(payload.scale_device)
    
    # 수량 업데이트 시 부피 재계산
    if payload.quantity is not None:
        update_data["quantity"] = payload.quantity
        if reagent["density"]:
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
    
    # 밀도가 있으면 부피도 업데이트
    if reagent["density"]:
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
    
    # 밀도가 있으면 부피도 업데이트
    if reagent["density"]:
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
        if reagent["density"]:
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
    for r in all_reagents:
        if r.get("nfc_tag_uid") == tag:
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
    
    if reagent["density"]:
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
