"""FastAPI application providing reagent inventory management APIs."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional
from urllib.parse import quote

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas
from . import localdb
from .localdb import search_local
from .database import SessionLocal, init_db
from .utils import slugify

PUBCHEM_AUTOCOMPLETE_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound/name/{query}/json"
)
PUBCHEM_PROPERTY_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/"
    "MolecularFormula,CID/JSON"
)

app = FastAPI(title="Reagent-ology API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_unique_slug(db: Session, base: str, current_id: Optional[int] = None) -> str:
    slug = base or "reagent"
    candidate = slug
    suffix = 1
    while True:
        query = db.query(models.Reagent).filter(models.Reagent.slug == candidate)
        if current_id is not None:
            query = query.filter(models.Reagent.id != current_id)
        if not query.first():
            return candidate
        candidate = f"{slug}-{suffix}"
        suffix += 1


def reagent_to_schema(reagent: models.Reagent) -> schemas.ReagentOut:
    payload = {
        "id": reagent.id,
        "slug": reagent.slug,
        "name": reagent.name,
        "formula": reagent.formula,
        "cas": reagent.cas,
        "location": reagent.location,
        "storage": reagent.storage,
        "expiry": reagent.expiry,
        "hazard": reagent.hazard,
        "ghs": reagent.ghs_list(),
        "disposal": reagent.disposal,
        "density": reagent.density,
        "volume_ml": reagent.volume_ml,
        "nfc_tag_uid": reagent.nfc_tag_uid,
        "scale_device": reagent.scale_device,
        "quantity": reagent.quantity,
        "used": reagent.used,
        "discarded": reagent.discarded,
        "created_at": reagent.created_at,
        "updated_at": reagent.updated_at,
    }
    return schemas.ReagentOut(**payload)


def usage_to_schema(log: models.UsageLog) -> schemas.UsageLogOut:
    payload = {
        "id": log.id,
        "prev_qty": log.prev_qty,
        "new_qty": log.new_qty,
        "delta": log.delta,
        "source": log.source,
        "note": log.note,
        "created_at": log.created_at,
    }
    return schemas.UsageLogOut(**payload)


def get_reagent_or_404(db: Session, identifier: str) -> models.Reagent:
    reagent: Optional[models.Reagent]
    if identifier.isdigit():
        reagent = db.query(models.Reagent).filter(models.Reagent.id == int(identifier)).first()
    else:
        reagent = db.query(models.Reagent).filter(models.Reagent.slug == identifier).first()
    if not reagent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    return reagent


def apply_measurement_update(
    reagent: models.Reagent,
    *,
    new_mass: Optional[float],
    new_volume: Optional[float],
    source: str,
    note: Optional[str],
    db: Session,
) -> schemas.ReagentOut:
    if new_mass is None and new_volume is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide new_quantity, measured_mass, or measured_volume",
        )

    prev_mass = reagent.quantity or 0.0

    mass = new_mass
    volume = new_volume

    if mass is None and volume is not None:
        if reagent.density:
            mass = volume * reagent.density
        else:
            mass = volume

    if volume is None and mass is not None:
        if reagent.density:
            volume = mass / reagent.density
        else:
            reagent.volume_ml = None

    if mass is not None:
        reagent.quantity = mass
    if volume is not None:
        reagent.volume_ml = volume

    delta = (reagent.quantity or 0.0) - prev_mass

    log = models.UsageLog(
        reagent_id=reagent.id,
        prev_qty=prev_mass,
        new_qty=reagent.quantity or 0.0,
        delta=delta,
        source=source,
        note=note,
    )
    db.add(log)
    db.commit()
    db.refresh(reagent)
    return reagent_to_schema(reagent)


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


@app.on_event("startup")
def on_startup() -> None:
    init_db()


async def get_db() -> AsyncGenerator[Session, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/reagents", response_model=List[schemas.ReagentOut])
def list_reagents(db: Session = Depends(get_db)) -> List[schemas.ReagentOut]:
    reagents = db.query(models.Reagent).order_by(models.Reagent.created_at.asc()).all()
    return [reagent_to_schema(r) for r in reagents]


@app.post(
    "/api/reagents",
    response_model=schemas.ReagentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_reagent(
    payload: schemas.ReagentCreate, db: Session = Depends(get_db)
) -> schemas.ReagentOut:
    base_slug = slugify(payload.name, payload.cas)
    slug = ensure_unique_slug(db, base_slug)

    volume_ml = payload.volume_ml
    if volume_ml is None and payload.density:
        volume_ml = payload.quantity / payload.density

    reagent = models.Reagent(
        slug=slug,
        name=payload.name,
        formula=payload.formula,
        cas=payload.cas,
        location=payload.location,
        storage=payload.storage,
        expiry=payload.expiry,
        hazard=payload.hazard,
        disposal=payload.disposal,
        density=payload.density,
        volume_ml=volume_ml,
        nfc_tag_uid=normalize_optional_string(payload.nfc_tag_uid),
        scale_device=normalize_optional_string(payload.scale_device),
        quantity=payload.quantity,
        used=payload.used,
        discarded=payload.discarded,
    )
    reagent.set_ghs(payload.ghs)

    db.add(reagent)
    db.commit()
    db.refresh(reagent)
    return reagent_to_schema(reagent)


@app.get("/api/reagents/{identifier}", response_model=schemas.ReagentOut)
def get_reagent(identifier: str, db: Session = Depends(get_db)) -> schemas.ReagentOut:
    reagent = get_reagent_or_404(db, identifier)
    return reagent_to_schema(reagent)


@app.put("/api/reagents/{identifier}", response_model=schemas.ReagentOut)
def update_reagent(
    identifier: str,
    payload: schemas.ReagentUpdate,
    db: Session = Depends(get_db),
) -> schemas.ReagentOut:
    reagent = get_reagent_or_404(db, identifier)

    if payload.name is not None:
        reagent.name = payload.name
    if payload.formula is not None:
        reagent.formula = payload.formula
    if payload.cas is not None:
        reagent.cas = payload.cas
    if payload.location is not None:
        reagent.location = payload.location
    if payload.storage is not None:
        reagent.storage = payload.storage
    if payload.expiry is not None:
        reagent.expiry = payload.expiry
    if payload.hazard is not None:
        reagent.hazard = payload.hazard
    if payload.ghs is not None:
        reagent.set_ghs(payload.ghs)
    if payload.disposal is not None:
        reagent.disposal = payload.disposal
    if payload.density is not None:
        reagent.density = payload.density
        if reagent.density and reagent.quantity is not None:
            reagent.volume_ml = reagent.quantity / reagent.density
    if payload.volume_ml is not None:
        reagent.volume_ml = payload.volume_ml
        if reagent.density and payload.quantity is None:
            reagent.quantity = reagent.volume_ml * reagent.density
    if payload.nfc_tag_uid is not None:
        reagent.nfc_tag_uid = normalize_optional_string(payload.nfc_tag_uid)
    if payload.scale_device is not None:
        reagent.scale_device = normalize_optional_string(payload.scale_device)
    if payload.quantity is not None:
        reagent.quantity = payload.quantity
        if reagent.density:
            reagent.volume_ml = reagent.quantity / reagent.density
    if payload.used is not None:
        reagent.used = payload.used
    if payload.discarded is not None:
        reagent.discarded = payload.discarded

    if payload.name is not None or payload.cas is not None:
        new_slug = slugify(reagent.name, reagent.cas)
        reagent.slug = ensure_unique_slug(db, new_slug, current_id=reagent.id)

    db.commit()
    db.refresh(reagent)
    return reagent_to_schema(reagent)


@app.delete(
    "/api/reagents/{identifier}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_reagent(identifier: str, db: Session = Depends(get_db)) -> Response:
    reagent = get_reagent_or_404(db, identifier)
    db.delete(reagent)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/reagents/{identifier}/use", response_model=schemas.ReagentOut)
def use_reagent(
    identifier: str,
    payload: schemas.UseRequest,
    db: Session = Depends(get_db),
) -> schemas.ReagentOut:
    reagent = get_reagent_or_404(db, identifier)
    if reagent.quantity < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient quantity")
    prev = reagent.quantity
    reagent.quantity = max(0.0, reagent.quantity - payload.amount)
    reagent.used += payload.amount

    log = models.UsageLog(
        reagent_id=reagent.id,
        prev_qty=prev,
        new_qty=reagent.quantity,
        delta=-payload.amount,
        source="use",
        note=payload.note,
    )
    db.add(log)
    db.commit()
    db.refresh(reagent)
    return reagent_to_schema(reagent)


@app.post("/api/reagents/{identifier}/discard", response_model=schemas.ReagentOut)
def discard_reagent(
    identifier: str,
    payload: schemas.UseRequest,
    db: Session = Depends(get_db),
) -> schemas.ReagentOut:
    reagent = get_reagent_or_404(db, identifier)
    if reagent.quantity < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient quantity")
    prev = reagent.quantity
    reagent.quantity = max(0.0, reagent.quantity - payload.amount)
    reagent.discarded += payload.amount

    log = models.UsageLog(
        reagent_id=reagent.id,
        prev_qty=prev,
        new_qty=reagent.quantity,
        delta=-payload.amount,
        source="discard",
        note=payload.note,
    )
    db.add(log)
    db.commit()
    db.refresh(reagent)
    return reagent_to_schema(reagent)


@app.post("/api/reagents/{identifier}/measurement", response_model=schemas.ReagentOut)
def update_measurement(
    identifier: str,
    payload: schemas.MeasurementRequest,
    db: Session = Depends(get_db),
) -> schemas.ReagentOut:
    reagent = get_reagent_or_404(db, identifier)
    mass = payload.measured_mass
    if mass is None:
        mass = payload.new_quantity
    volume = payload.measured_volume
    return apply_measurement_update(
        reagent,
        new_mass=mass,
        new_volume=volume,
        source=payload.source,
        note=payload.note,
        db=db,
    )


@app.post("/api/measurements/weight", response_model=schemas.ReagentOut)
def record_weight_measurement(
    payload: schemas.WeightMeasurementRequest,
    db: Session = Depends(get_db),
) -> schemas.ReagentOut:
    tag = payload.nfc_tag_uid.strip()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NFC tag UID cannot be empty",
        )
    reagent = (
        db.query(models.Reagent)
        .filter(models.Reagent.nfc_tag_uid == tag)
        .first()
    )
    if not reagent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reagent not found for provided NFC tag",
        )

    return apply_measurement_update(
        reagent,
        new_mass=payload.measured_mass,
        new_volume=None,
        source=payload.source,
        note=payload.note,
        db=db,
    )


@app.get(
    "/api/reagents/{identifier}/usage",
    response_model=List[schemas.UsageLogOut],
)
def list_usage(identifier: str, db: Session = Depends(get_db)) -> List[schemas.UsageLogOut]:
    reagent = get_reagent_or_404(db, identifier)
    logs = (
        db.query(models.UsageLog)
        .filter(models.UsageLog.reagent_id == reagent.id)
        .order_by(models.UsageLog.created_at.desc())
        .all()
    )
    return [usage_to_schema(log) for log in logs]


@app.post("/api/reagents/reset-stats")
def reset_stats(db: Session = Depends(get_db)) -> Dict[str, str]:
    reagents = db.query(models.Reagent).all()
    for reagent in reagents:
        reagent.used = 0.0
        reagent.discarded = 0.0
    db.commit()
    return {"status": "ok"}


@app.get(
    "/api/autocomplete",
    response_model=schemas.AutocompleteResponse,
)
async def autocomplete(
    q: str = Query(..., min_length=2, max_length=60),
    limit: int = Query(8, ge=1, le=20),
) -> schemas.AutocompleteResponse:
    # 1) local 우선
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
    return schemas.AutocompleteResponse(suggestions=search_local(q, limit=limit))


# Local autocomplete DB CRUD endpoints
@app.get("/api/autocomplete/local-db", response_model=List[schemas.LocalChemOut])
def list_local_db() -> List[schemas.LocalChemOut]:
    return [schemas.LocalChemOut(**item) for item in localdb.list_all()]


@app.post("/api/autocomplete/local-db", response_model=schemas.LocalChemOut, status_code=201)
def add_local_db(payload: schemas.LocalChemCreate) -> schemas.LocalChemOut:
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
    try:
        localdb.delete_item(name)
        return Response(status_code=204)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not found")


@app.put("/api/autocomplete/local-db/{name}", response_model=schemas.LocalChemOut)
def update_local_db(name: str, payload: schemas.LocalChemCreate) -> schemas.LocalChemOut:
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