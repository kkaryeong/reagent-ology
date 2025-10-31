"""CSV-backed local autocomplete database with basic CRUD and search.

CSV schema:
    name,formula,synonyms,cas,storage,ghs,disposal,density
    Sodium Chloride,NaCl,"Salt;Table Salt",7647-14-5,RT,"Irritant","일반폐기물",2.165

The CSV file is stored under reagent-ology/data/autocomplete.csv
"""
from __future__ import annotations

import csv
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "autocomplete.csv"
_lock = threading.Lock()


@dataclass
class Chemical:
    name: str
    formula: str
    synonyms: List[str] = field(default_factory=list)
    cas: Optional[str] = None
    storage: Optional[str] = None
    ghs: List[str] = field(default_factory=list)
    disposal: Optional[str] = None
    density: Optional[float] = None


def _read_all() -> List[Chemical]:
    DATA_DIR.mkdir(exist_ok=True)
    if not CSV_PATH.exists():
        return []
    items: List[Chemical] = []
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            formula = (row.get("formula") or "").strip()
            syn = (row.get("synonyms") or "").strip()
            ghs_raw = (row.get("ghs") or "").strip()
            disposal = (row.get("disposal") or "").strip() or None
            cas = (row.get("cas") or "").strip() or None
            storage = (row.get("storage") or "").strip() or None
            density_raw = (row.get("density") or "").strip()

            synonyms = [s.strip() for s in syn.split(";") if s.strip()] if syn else []
            ghs = [s.strip() for s in ghs_raw.split(";") if s.strip()] if ghs_raw else []
            density: Optional[float]
            if density_raw:
                try:
                    density = float(density_raw)
                except ValueError:
                    density = None
            else:
                density = None

            if name and formula:
                items.append(
                    Chemical(
                        name=name,
                        formula=formula,
                        synonyms=synonyms,
                        cas=cas,
                        storage=storage,
                        ghs=ghs,
                        disposal=disposal,
                        density=density,
                    )
                )
    return items


def _write_all(items: List[Chemical]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "formula",
                "synonyms",
                "cas",
                "storage",
                "ghs",
                "disposal",
                "density",
            ],
        )
        writer.writeheader()
        for c in items:
            writer.writerow({
                "name": c.name,
                "formula": c.formula,
                "synonyms": ";".join(c.synonyms) if c.synonyms else "",
                "cas": c.cas or "",
                "storage": c.storage or "",
                "ghs": ";".join(c.ghs) if c.ghs else "",
                "disposal": c.disposal or "",
                "density": f"{c.density}" if c.density is not None else "",
            })


def list_all() -> List[dict]:
    with _lock:
        items = _read_all()
    return [
        {
            "name": c.name,
            "formula": c.formula,
            "synonyms": c.synonyms,
            "cas": c.cas,
            "storage": c.storage,
            "ghs": c.ghs,
            "disposal": c.disposal,
            "density": c.density,
        }
        for c in items
    ]


def add_item(
    name: str,
    formula: str,
    synonyms: Optional[List[str]] = None,
    *,
    cas: Optional[str] = None,
    storage: Optional[str] = None,
    ghs: Optional[List[str]] = None,
    disposal: Optional[str] = None,
    density: Optional[float] = None,
) -> dict:
    if not name or not formula:
        raise ValueError("name and formula are required")
    syns = [s.strip() for s in (synonyms or []) if s.strip()]
    ghs_clean = [s.strip() for s in (ghs or []) if s.strip()]
    cas_clean = cas.strip() if cas else None
    storage_clean = storage.strip() if storage else None
    disposal_clean = disposal.strip() if disposal else None
    density_clean = None
    if density is not None:
        if density <= 0:
            raise ValueError("density must be greater than zero")
        density_clean = float(density)
    with _lock:
        items = _read_all()
        if any(c.name.lower() == name.lower() for c in items):
            raise FileExistsError("duplicate name")
        items.append(
            Chemical(
                name=name.strip(),
                formula=formula.strip(),
                synonyms=syns,
                cas=cas_clean,
                storage=storage_clean,
                ghs=ghs_clean,
                disposal=disposal_clean,
                density=density_clean,
            )
        )
        items.sort(key=lambda c: c.name.lower())
        _write_all(items)
    return {
        "name": name.strip(),
        "formula": formula.strip(),
        "synonyms": syns,
        "cas": cas_clean,
        "storage": storage_clean,
        "ghs": ghs_clean,
        "disposal": disposal_clean,
        "density": density_clean,
    }


def delete_item(name: str) -> None:
    with _lock:
        items = _read_all()
        new_items = [c for c in items if c.name.lower() != name.lower()]
        if len(new_items) == len(items):
            raise FileNotFoundError("not found")
        _write_all(new_items)


def update_item(
    original_name: str,
    *,
    name: Optional[str] = None,
    formula: Optional[str] = None,
    synonyms: Optional[List[str]] = None,
    cas: Optional[str] = None,
    storage: Optional[str] = None,
    ghs: Optional[List[str]] = None,
    disposal: Optional[str] = None,
    density: Optional[float] = None,
) -> dict:
    with _lock:
        items = _read_all()
        idx = next((i for i, c in enumerate(items) if c.name.lower() == original_name.lower()), None)
        if idx is None:
            raise FileNotFoundError("not found")
        current = items[idx]
        new_name = name.strip() if name is not None else current.name
        new_formula = formula.strip() if formula is not None else current.formula
        new_syns = [
            s.strip()
            for s in (synonyms if synonyms is not None else current.synonyms)
            if s.strip()
        ]
        new_ghs = [
            s.strip()
            for s in (ghs if ghs is not None else current.ghs)
            if s.strip()
        ]
        new_cas = cas.strip() if cas is not None and cas.strip() else (None if cas == "" else current.cas)
        if cas is None:
            new_cas = current.cas
        new_storage = (
            storage.strip()
            if storage is not None and storage.strip()
            else (None if storage == "" else current.storage)
        )
        if storage is None:
            new_storage = current.storage
        new_disposal = (
            disposal.strip()
            if disposal is not None and disposal.strip()
            else (None if disposal == "" else current.disposal)
        )
        if disposal is None:
            new_disposal = current.disposal
        if density is not None:
            if density <= 0:
                raise ValueError("density must be greater than zero")
            new_density = float(density)
        elif density == 0:  # pragma: no cover - explicit zero is invalid, retained for clarity
            raise ValueError("density must be greater than zero")
        else:
            new_density = current.density
        # Name change conflict check
        if new_name.lower() != current.name.lower() and any(c.name.lower() == new_name.lower() for c in items):
            raise FileExistsError("duplicate name")
        items[idx] = Chemical(
            name=new_name,
            formula=new_formula,
            synonyms=new_syns,
            cas=new_cas,
            storage=new_storage,
            ghs=new_ghs,
            disposal=new_disposal,
            density=new_density,
        )
        items.sort(key=lambda c: c.name.lower())
        _write_all(items)
    return {
        "name": new_name,
        "formula": new_formula,
        "synonyms": new_syns,
        "cas": new_cas,
        "storage": new_storage,
        "ghs": new_ghs,
        "disposal": new_disposal,
        "density": new_density,
    }


def search_local(query: str, limit: int = 8) -> List[dict]:
    if not query:
        return []
    q = query.strip().lower()
    with _lock:
        items = _read_all()

    scored: List[tuple[int, Chemical]] = []
    for chem in items:
        name_l = chem.name.lower()
        syns_l = [s.lower() for s in chem.synonyms]
        score = None
        if name_l.startswith(q):
            score = 0
        elif any(s.startswith(q) for s in syns_l):
            score = 1
        elif q in name_l:
            score = 2
        elif any(q in s for s in syns_l):
            score = 3
        if score is not None:
            scored.append((score, chem))

    scored.sort(key=lambda t: (t[0], t[1].name))
    results = []
    for _, chem in scored[:limit]:
        results.append(
            {
                "name": chem.name,
                "formula": chem.formula,
                "cid": None,
                "cas": chem.cas,
                "storage": chem.storage,
                "ghs": chem.ghs,
                "disposal": chem.disposal,
                "density": chem.density,
            }
        )
    return results
