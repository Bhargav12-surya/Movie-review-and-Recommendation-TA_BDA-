"""Attach locally supplied CineScope poster/backdrop assets to matching MovieLens rows."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from backend.app.core.config import ROOT, get_settings
from backend.app.database.session import make_engine, get_session_factory
from backend.app.models import Movie

LOCAL_TITLE_MAP = {
    "Interstellar": "Interstellar (2014)",
    "Arrival": "Arrival (2016)",
    "Her": "Her (2013)",
    "Blade Runner 2049": "Blade Runner 2049 (2017)",
    "Inception": "Inception (2010)",
    "Eternal Sunshine of the Spotless Mind": "Eternal Sunshine of the Spotless Mind (2004)",
    "The Martian": "The Martian (2015)",
    "La La Land": "La La Land (2016)",
    "The Matrix": "Matrix, The (1999)",
    "Everything Everywhere All at Once": "Everything Everywhere All at Once (2022)",
    "Coherence": "Coherence (2013)",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Commit updates to PostgreSQL.")
    args = parser.parse_args()

    catalog_path = ROOT / "temp/CineScope/data/demo/catalog.json"
    if not catalog_path.is_file():
        raise FileNotFoundError(f"Missing local asset catalog: {catalog_path}")

    settings = get_settings()
    poster_dir = (ROOT / settings.poster_cache).resolve()
    entries = json.loads(catalog_path.read_text(encoding="utf-8"))

    engine = make_engine(settings)
    factory = get_session_factory(engine)
    matched = []
    with factory() as session:
        for item in entries:
            ml_title = LOCAL_TITLE_MAP.get(item.get("title", ""))
            if not ml_title:
                continue
            row = session.scalar(select(Movie).where(Movie.title == ml_title).limit(1))
            if row is None:
                continue

            poster_name = Path(item.get("poster", "")).name
            backdrop_name = Path(item.get("backdrop", "")).name
            updates = {}
            if poster_name and (poster_dir / poster_name).is_file():
                updates["poster_path"] = poster_name
            if backdrop_name and (poster_dir / backdrop_name).is_file():
                updates["backdrop_path"] = backdrop_name
            if not row.overview and item.get("overview"):
                updates["overview"] = item["overview"]
            if not row.release_date and item.get("year"):
                updates["release_date"] = f"{item['year']}-01-01"
            if not row.runtime_minutes and item.get("runtime"):
                updates["runtime_minutes"] = int(item["runtime"])
            if item.get("themes"):
                features = dict(row.features or {})
                if not features.get("themes"):
                    features["themes"] = item["themes"]
                    updates["features"] = features

            matched.append({"movie_id": row.id, "title": row.title, "fields": sorted(updates.keys())})
            if args.execute:
                for key, value in updates.items():
                    setattr(row, key, value)

        if args.execute:
            session.commit()
    engine.dispose()
    print(json.dumps({"executed": args.execute, "matched_count": len(matched), "matched": matched}, indent=2))


if __name__ == "__main__":
    main()

