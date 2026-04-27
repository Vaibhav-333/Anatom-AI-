"""
care_navigator.py — Free proxy using OpenStreetMap / Overpass API.

No API key required. All data sourced from OpenStreetMap contributors.
Automatic failover across 4 Overpass mirrors — handles 429 / 503 gracefully.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["Care Navigator"])

# ── Multiple Overpass mirrors — tried in order on 429/503/timeout ──────────

_OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "NeuroMapper/1.0 (medical-ai-app; contact@neuromapper.app)",
}

# ── Overpass type filters ──────────────────────────────────────────────────

_TYPE_FILTERS: dict[str, str] = {
    "hospital": '["amenity"~"hospital|clinic"]',
    "doctor":   '["amenity"~"clinic|doctors|dentist"]',
    "pharmacy": '["amenity"~"pharmacy|chemist"]',
}

# Broad filter — used only for truly custom keywords (e.g. "neurologist")
_BROAD_FILTER = '["amenity"~"hospital|clinic|doctors|pharmacy|dentist|healthcare|physiotherapist|nursing_home"]'

# ── Keyword → type resolver ────────────────────────────────────────────────
# Maps plain-English words a user might type to their fast type-filter key.
# Prevents "hospitals" from triggering the slow _BROAD_FILTER.

_KEYWORD_TO_TYPE: dict[str, str] = {
    "hospital": "hospital", "hospitals": "hospital",
    "clinic": "doctor", "clinics": "doctor",
    "doctor": "doctor", "doctors": "doctor",
    "gp": "doctor", "general practitioner": "doctor",
    "pharmacy": "pharmacy", "pharmacies": "pharmacy",
    "chemist": "pharmacy", "drug store": "pharmacy", "drugstore": "pharmacy",
    "dentist": "doctor", "dental": "doctor",
    "medical": "hospital", "health centre": "hospital", "health center": "hospital",
    "dispensary": "pharmacy",
}

# ── Request model ──────────────────────────────────────────────────────────

class NearbySearchRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius: int = Field(5000, ge=500, le=50000)
    type: str = Field("hospital")
    keyword: Optional[str] = Field(None, max_length=200)


# ── Overpass helpers ───────────────────────────────────────────────────────

def _post_to_mirror(url: str, query: str, timeout: int = 22) -> dict:
    """POST query to a single Overpass mirror. Raises on any HTTP/network error."""
    body = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=body, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _fetch_overpass(query: str) -> dict:
    """
    Try each mirror in order.
    On 429 / 503 / timeout → wait 0.4 s then try the next mirror.
    Raises the last exception only if every mirror fails.
    """
    last_exc: Exception = RuntimeError("No Overpass mirrors configured")

    for mirror in _OVERPASS_MIRRORS:
        try:
            return _post_to_mirror(mirror, query)
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 503, 504):
                time.sleep(0.4)   # brief cooldown before next mirror
                continue
            raise                 # 4xx other than rate-limit → propagate immediately
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            time.sleep(0.3)
            continue

    raise last_exc


def _build_query(
    lat: float,
    lng: float,
    radius: int,
    place_type: str,
    keyword: Optional[str],
) -> str:
    """
    Build an Overpass QL query.
    Resolution order for the amenity filter:
      1. Keyword maps to a known type  → fast type-specific filter
      2. Keyword is a custom specialist → broad medical filter
      3. No keyword                     → type-specific filter from place_type
    Only node + way are queried (relations are slow and rarely add useful POIs).
    Overpass timeout=18 keeps it below the Python socket timeout (22 s).
    """
    if keyword:
        mapped = _KEYWORD_TO_TYPE.get(keyword.lower().strip())
        amenity_filter = (
            _TYPE_FILTERS[mapped]
            if mapped
            else _BROAD_FILTER
        )
    else:
        amenity_filter = _TYPE_FILTERS.get(place_type, _TYPE_FILTERS["hospital"])

    around = f"(around:{radius},{lat},{lng})"

    return (
        f"[out:json][timeout:18];\n"
        f"(\n"
        f"  node{amenity_filter}{around};\n"
        f"  way{amenity_filter}{around};\n"
        f");\n"
        f"out center tags;"
    )


def _normalize(el: dict) -> Optional[dict]:
    """Convert a single Overpass element to the NearbyPlace shape."""
    el_type = el.get("type")
    if el_type not in ("node", "way"):
        return None

    if el_type == "node":
        lat = el.get("lat")
        lng = el.get("lon")
    else:
        center = el.get("center", {})
        lat = center.get("lat")
        lng = center.get("lon")

    if lat is None or lng is None:
        return None

    prefix = "n" if el_type == "node" else "w"
    place_id = f"{prefix}{el['id']}"

    tags = el.get("tags", {})
    name = (
        tags.get("name")
        or tags.get("name:en")
        or tags.get("operator")
        or "Unnamed facility"
    )

    # Build vicinity string from address tags
    addr_parts = [
        tags.get("addr:housenumber", ""),
        tags.get("addr:street", ""),
        tags.get("addr:suburb", ""),
        tags.get("addr:city", ""),
    ]
    vicinity = ", ".join(p for p in addr_parts if p)
    if not vicinity:
        # Fallback: use district / city tag directly
        vicinity = tags.get("addr:district") or tags.get("is_in:city") or ""

    return {
        "place_id": place_id,
        "name": name,
        "vicinity": vicinity,
        "lat": lat,
        "lng": lng,
        "rating": None,             # OSM has no star ratings
        "user_ratings_total": None,
        "open_now": None,           # Would need opening_hours.js to evaluate
        "types": [t for t in [tags.get("amenity"), tags.get("healthcare")] if t],
    }


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/get-nearby-places")
async def get_nearby_places(req: NearbySearchRequest) -> dict:
    """
    Return nearby healthcare facilities via Overpass / OpenStreetMap.
    Automatically retries across 4 mirrors on rate-limit (429).
    No API key required. Returns up to 50 deduplicated results.
    """
    query = _build_query(req.lat, req.lng, req.radius, req.type, req.keyword)

    try:
        data = await asyncio.to_thread(_fetch_overpass, query)
    except urllib.error.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Overpass API error {exc.code}: {exc.reason}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Overpass unreachable (all mirrors tried): {exc}",
        ) from exc

    elements = data.get("elements", [])
    if not elements:
        return {"results": [], "status": "ZERO_RESULTS"}

    # Normalize
    raw = [_normalize(el) for el in elements]
    raw = [r for r in raw if r is not None]

    # Deduplicate: same name + coordinates within ~11 m (4 decimal places)
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for r in raw:
        key = (r["name"].lower().strip(), round(r["lat"], 4), round(r["lng"], 4))
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return {"results": deduped[:50], "status": "OK"}


@router.get("/get-place-details/{place_id}")
async def get_place_details(place_id: str) -> dict:
    """
    Return enriched OSM details for a single place: phone, hours, website.
    place_id format: "n{id}" (node), "w{id}" (way), or "r{id}" (relation).
    Reviews are unavailable in OSM and always return as [].
    """
    if not place_id or len(place_id) > 100:
        raise HTTPException(status_code=400, detail="Invalid place_id")

    prefix = place_id[0] if place_id else ""
    osm_id = place_id[1:]

    if not osm_id.isdigit() or prefix not in ("n", "w", "r"):
        raise HTTPException(
            status_code=400,
            detail="Invalid place_id format (expected n<id>, w<id>, or r<id>)",
        )

    type_map = {"n": "node", "w": "way", "r": "relation"}
    query = f"[out:json];{type_map[prefix]}({osm_id});out body;"

    try:
        data = await asyncio.to_thread(_fetch_overpass, query)
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Overpass error {exc.code}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Overpass unreachable: {exc}") from exc

    empty: dict = {
        "place_id": place_id,
        "formatted_address": None,
        "formatted_phone_number": None,
        "opening_hours": None,
        "rating": None,
        "user_ratings_total": None,
        "reviews": [],
        "website": None,
    }

    elements = data.get("elements", [])
    if not elements:
        return empty

    tags = elements[0].get("tags", {})

    addr_parts = [
        tags.get("addr:housenumber", ""),
        tags.get("addr:street", ""),
        tags.get("addr:suburb", ""),
        tags.get("addr:city", ""),
        tags.get("addr:state", ""),
        tags.get("addr:country", ""),
    ]
    formatted_address = ", ".join(p for p in addr_parts if p) or None

    oh_raw = tags.get("opening_hours")
    opening_hours = (
        {"open_now": None, "weekday_text": [oh_raw]}
        if oh_raw
        else None
    )

    return {
        "place_id": place_id,
        "formatted_address": formatted_address,
        "formatted_phone_number": (
            tags.get("phone")
            or tags.get("contact:phone")
            or tags.get("contact:mobile")
            or None
        ),
        "opening_hours": opening_hours,
        "rating": None,
        "user_ratings_total": None,
        "reviews": [],
        "website": (
            tags.get("website")
            or tags.get("contact:website")
            or tags.get("url")
            or None
        ),
    }
