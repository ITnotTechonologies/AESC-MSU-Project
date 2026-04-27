#!/usr/bin/env python3
"""
Import product image URLs from CSV into PostgreSQL.

Compatible CSV columns:
- seed_name (preferred)
- product_name (fallback)
- name (fallback)
- direct_image_url (preferred URL to actual image)
- image_url (fallback)
- fiveka_product_url (ignored unless it's the only URL you provide)

Rows without a direct image URL are skipped so startup won't fail.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@dataclass
class Row:
    product_name: str
    image_url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import product image URLs from CSV into PostgreSQL."
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        required=True,
        type=Path,
        help="Path to CSV file with image mappings.",
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=os.getenv("DATABASE_URL"),
        help="SQLAlchemy/PostgreSQL database URL. Defaults to DATABASE_URL env var.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes to DB. If omitted, script runs in dry-run mode.",
    )
    return parser.parse_args()


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def first_nonempty(*values: str | None) -> str:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def extract_rows(csv_path: Path) -> list[Row]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows: list[Row] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")

        fieldnames = {name.strip() for name in reader.fieldnames if name}

        name_keys = ("seed_name", "product_name", "name")
        url_keys = ("direct_image_url", "image_url")

        if not any(k in fieldnames for k in name_keys):
            raise ValueError(
                f"CSV must contain one of columns: {', '.join(name_keys)}"
            )

        if not any(k in fieldnames for k in url_keys):
            raise ValueError(
                f"CSV must contain one of columns: {', '.join(url_keys)}"
            )

        for raw in reader:
            product_name = first_nonempty(raw.get("seed_name"), raw.get("product_name"), raw.get("name"))
            image_url = first_nonempty(raw.get("direct_image_url"), raw.get("image_url"))

            # Skip rows that don't have a direct image url.
            if not product_name or not image_url:
                continue

            rows.append(Row(product_name=product_name, image_url=image_url))

    return rows


def fetch_existing_product_names(engine: Engine, product_names: Iterable[str]) -> set[str]:
    names = list(dict.fromkeys(product_names))
    if not names:
        return set()

    query = text("SELECT name FROM products WHERE name = ANY(:names)")
    with engine.connect() as conn:
        result = conn.execute(query, {"names": names})
        return {row[0] for row in result.fetchall()}


def update_images(engine: Engine, rows: list[Row], apply: bool) -> tuple[int, int, int]:
    """
    Returns: (parsed_rows, matched_rows, missing_rows)
    """
    existing = fetch_existing_product_names(engine, [r.product_name for r in rows])

    matched_rows = [r for r in rows if r.product_name in existing]
    missing_rows = len(rows) - len(matched_rows)

    if not apply:
        return len(rows), len(matched_rows), missing_rows

    stmt = text(
        """
        UPDATE products
        SET image_url = :image_url
        WHERE name = :name
        """
    )

    with engine.begin() as conn:
        for row in matched_rows:
            conn.execute(stmt, {"name": row.product_name, "image_url": row.image_url})

    return len(rows), len(matched_rows), missing_rows


def main() -> int:
    args = parse_args()

    if not args.database_url:
        print(
            "DATABASE_URL is not set. Pass --database-url or set env var DATABASE_URL.",
            file=sys.stderr,
        )
        return 2

    try:
        rows = extract_rows(args.csv_path)
    except Exception as exc:
        print(f"Failed to read CSV: {exc}", file=sys.stderr)
        return 1

    if not rows:
        print("No valid rows with direct_image_url found in CSV.", file=sys.stderr)
        return 1

    engine = get_engine(args.database_url)

    try:
        parsed, matched, missing = update_images(engine, rows, apply=args.apply)
    except Exception as exc:
        print(f"DB update failed: {exc}", file=sys.stderr)
        return 1

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] CSV rows with direct image URLs: {parsed}")
    print(f"[{mode}] Matched products in DB: {matched}")
    print(f"[{mode}] Missing product names in DB: {missing}")

    if not args.apply:
        print("Re-run with --apply to write changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
