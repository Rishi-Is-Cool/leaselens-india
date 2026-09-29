"""Load data/statute_kb/leaselens_statute_kb.json into Postgres, via the project's own
SQLAlchemy session (app.db.get_session), not a separate raw-psycopg connection.

Optional: retrieval and Phase 4 work entirely from the JSON files and do not require
this. Run it only if something needs the KB queryable from Postgres directly (e.g.
future admin tooling).

    python scripts/load_statute_kb_postgres.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import create_tables, get_session  # noqa: E402
from app.models import StatuteEntry  # noqa: E402
from app.statute_kb.retrieval import load_kb  # noqa: E402


def main() -> None:
    create_tables()
    kb = load_kb()
    session = next(get_session())
    try:
        for entry in kb["entries"]:
            row = session.get(StatuteEntry, entry["id"]) or StatuteEntry(id=entry["id"])
            row.citation = entry["citation"]
            row.excerpt_text = entry["excerpt_text"]
            row.source_url = entry["source_url"]
            row.jurisdiction = entry["jurisdiction"]
            row.topic_tags = entry["topic_tags"]
            row.last_verified_date = entry["last_verified_date"]
            session.merge(row)
        session.commit()
        print(f"Loaded {len(kb['entries'])} statute entries into Postgres.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
