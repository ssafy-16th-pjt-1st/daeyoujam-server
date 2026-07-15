import json
import logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.place import Place

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def normalize(value):
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def to_float(value):
    value = normalize(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value):
    value = normalize(value)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def iter_items(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    content_type = payload.get("contentType") or path.stem.replace("대전_충청권_", "")
    content_type_id = to_int(payload.get("contentTypeId"))
    for item in payload.get("items", []):
        yield content_type, content_type_id, item


def seed_places_if_empty(db: Session) -> int:
    existing_count = db.scalar(select(func.count(Place.id))) or 0
    if existing_count:
        return 0

    inserted = 0
    if not RAW_DIR.exists():
        logger.warning("Place seed skipped: raw data directory does not exist: %s", RAW_DIR)
        return 0

    for path in sorted(RAW_DIR.glob("*.json")):
        for content_type, payload_content_type_id, item in iter_items(path):
            content_id = to_int(item.get("contentid"))
            if not content_id:
                continue
            db.add(
                Place(
                    content_id=content_id,
                    content_type_id=to_int(item.get("contenttypeid")) or payload_content_type_id,
                    content_type=content_type,
                    title=normalize(item.get("title")) or "(제목 없음)",
                    addr1=normalize(item.get("addr1")),
                    addr2=normalize(item.get("addr2")),
                    zipcode=normalize(item.get("zipcode")),
                    tel=normalize(item.get("tel")),
                    mapx=to_float(item.get("mapx")),
                    mapy=to_float(item.get("mapy")),
                    mlevel=to_int(item.get("mlevel")),
                    first_image=normalize(item.get("firstimage")),
                    first_image2=normalize(item.get("firstimage2")),
                    created_time=normalize(item.get("createdtime")),
                    modified_time=normalize(item.get("modifiedtime")),
                    copyright_type=normalize(item.get("cpyrhtDivCd")),
                    area_code=normalize(item.get("areacode")),
                    sigungu_code=normalize(item.get("sigungucode")),
                    region_code=normalize(item.get("lDongRegnCd")),
                    signgu_code=normalize(item.get("lDongSignguCd")),
                    category1=normalize(item.get("cat1")),
                    category2=normalize(item.get("cat2")),
                    category3=normalize(item.get("cat3")),
                    lcls_system1=normalize(item.get("lclsSystm1")),
                    lcls_system2=normalize(item.get("lclsSystm2")),
                    lcls_system3=normalize(item.get("lclsSystm3")),
                )
            )
            inserted += 1

    db.commit()
    logger.info("Place seed complete: inserted=%s", inserted)
    return inserted
