"""CSV-backed local autocomplete database with basic CRUD and search.

CSV schema:
    name,formula,synonyms
    Sodium Chloride,NaCl,"Salt;Table Salt"

The CSV file is stored under reagent-ology/data/autocomplete.csv
"""
from __future__ import annotations

import csv
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "autocomplete.csv"
_lock = threading.Lock()


@dataclass
class Chemical:
    name: str
    formula: str
    synonyms: List[str]


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
            synonyms = [s.strip() for s in syn.split(";") if s.strip()] if syn else []
            if name and formula:
                items.append(Chemical(name=name, formula=formula, synonyms=synonyms))
    return items


def _write_all(items: List[Chemical]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "formula", "synonyms"])
        writer.writeheader()
        for c in items:
            writer.writerow({
                "name": c.name,
                "formula": c.formula,
                "synonyms": ";".join(c.synonyms) if c.synonyms else "",
            })


def list_all() -> List[dict]:
    with _lock:
        items = _read_all()
    return [{"name": c.name, "formula": c.formula, "synonyms": c.synonyms} for c in items]


def add_item(name: str, formula: str, synonyms: Optional[List[str]] = None) -> dict:
    if not name or not formula:
        raise ValueError("name and formula are required")
    syns = [s.strip() for s in (synonyms or []) if s.strip()]
    with _lock:
        items = _read_all()
        if any(c.name.lower() == name.lower() for c in items):
            raise FileExistsError("duplicate name")
        items.append(Chemical(name=name.strip(), formula=formula.strip(), synonyms=syns))
        items.sort(key=lambda c: c.name.lower())
        _write_all(items)
    return {"name": name.strip(), "formula": formula.strip(), "synonyms": syns}


def delete_item(name: str) -> None:
    with _lock:
        items = _read_all()
        new_items = [c for c in items if c.name.lower() != name.lower()]
        if len(new_items) == len(items):
            raise FileNotFoundError("not found")
        _write_all(new_items)


def update_item(original_name: str, name: Optional[str] = None, formula: Optional[str] = None, synonyms: Optional[List[str]] = None) -> dict:
    with _lock:
        items = _read_all()
        idx = next((i for i, c in enumerate(items) if c.name.lower() == original_name.lower()), None)
        if idx is None:
            raise FileNotFoundError("not found")
        current = items[idx]
        new_name = name.strip() if name is not None else current.name
        new_formula = formula.strip() if formula is not None else current.formula
        new_syns = [s.strip() for s in (synonyms if synonyms is not None else current.synonyms) if s.strip()]
        # Name change conflict check
        if new_name.lower() != current.name.lower() and any(c.name.lower() == new_name.lower() for c in items):
            raise FileExistsError("duplicate name")
        items[idx] = Chemical(name=new_name, formula=new_formula, synonyms=new_syns)
        items.sort(key=lambda c: c.name.lower())
        _write_all(items)
    return {"name": new_name, "formula": new_formula, "synonyms": new_syns}


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
        results.append({"name": chem.name, "formula": chem.formula, "cid": None})
    return results
