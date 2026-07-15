import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Place  # noqa: E402,F401
from app.services.place_seed_service import seed_places_if_empty  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        inserted = seed_places_if_empty(db)
        print(f"seed complete: inserted={inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
