#!/usr/bin/env python3
"""InstaGuard: local case manager for suspected Instagram policy violations.

No login, scraping, private-profile bypass, or automated reporting.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlparse

DEFAULT_DB = Path.home() / ".instaguard" / "cases.db"
USERNAME = re.compile(r"^[A-Za-z0-9._]{1,30}$")
CATEGORIES = ("impersonation", "scam", "spam", "other")
STATUSES = ("new", "reviewing", "reported", "closed")


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_username(value):
    """Accept @username or a complete, canonical Instagram profile URL."""
    value = value.strip()
    if value.startswith(("https://", "http://")):
        parsed = urlparse(value)
        if (parsed.scheme != "https" or
                parsed.hostname not in ("instagram.com", "www.instagram.com") or
                parsed.port is not None or parsed.username or parsed.password or
                parsed.query or parsed.fragment):
            raise ValueError("Use um link HTTPS de perfil do Instagram sem parâmetros.")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 1:
            raise ValueError("Use o link de um perfil, não de uma publicação ou reel.")
        value = parts[0]
    else:
        value = value.lstrip("@")
    if not USERNAME.fullmatch(value):
        raise ValueError("Use @usuario ou https://www.instagram.com/usuario/")
    return value


def check_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Evidence must have a valid https:// URL.")
    if parsed.username or parsed.password:
        raise ValueError("Do not include usernames or passwords in evidence URLs.")
    return value


def connect(path):
    path = Path(path).expanduser()
    parent_was_present = path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Nunca altere permissões de diretórios já existentes de terceiros
    # (por exemplo, /tmp ou uma pasta escolhida pelo operador).
    if not parent_was_present or path.parent == DEFAULT_DB.parent:
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id),
            url TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.commit()
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return connection


def require_case(db, case_id):
    case = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        raise ValueError(f"Case #{case_id} does not exist.")
    return case


def get_case(db, case_id):
    item = dict(require_case(db, case_id))
    item["evidence"] = [
        dict(row) for row in db.execute(
            "SELECT id, url, description, created_at FROM evidence "
            "WHERE case_id = ? ORDER BY id", (case_id,)
        )
    ]
    return item


def parser():
    p = argparse.ArgumentParser(
        description="Manage investigation cases locally. No automated Instagram reports."
    )
    p.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    sub = p.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Create a case for a suspected account")
    add.add_argument("username")
    add.add_argument("--category", required=True, choices=CATEGORIES)
    add.add_argument("--reason", required=True, help="Describe the observed behavior")

    listing = sub.add_parser("list", help="Show cases")
    listing.add_argument("--status", choices=STATUSES)

    show = sub.add_parser("show", help="Show one case and its evidence")
    show.add_argument("id", type=int)

    evidence = sub.add_parser("evidence", help="Attach an evidence link")
    evidence.add_argument("id", type=int)
    evidence.add_argument("--url", required=True)
    evidence.add_argument("--description", required=True)

    status = sub.add_parser("status", help="Manually update a case")
    status.add_argument("id", type=int)
    status.add_argument("value", choices=STATUSES)

    sub.add_parser("stats", help="Show counts by status")

    export = sub.add_parser("export", help="Export cases to a local JSON file")
    export.add_argument("--output", required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    db = connect(args.db)
    try:
        if args.command == "add":
            username = clean_username(args.username)
            reason = args.reason.strip()
            if not reason:
                raise ValueError("Provide a specific reason supported by evidence.")
            time = timestamp()
            cur = db.execute(
                "INSERT INTO cases (username, category, reason, status, created_at, updated_at) "
                "VALUES (?, ?, ?, 'new', ?, ?)",
                (username, args.category, reason, time, time),
            )
            db.commit()
            print(f"Created case #{cur.lastrowid} for @{username}.")
        elif args.command == "list":
            if args.status:
                rows = db.execute(
                    "SELECT id, username, category, status FROM cases "
                    "WHERE status = ? ORDER BY id DESC", (args.status,)
                )
            else:
                rows = db.execute(
                    "SELECT id, username, category, status FROM cases ORDER BY id DESC"
                )
            result = list(rows)
            if not result:
                print("No cases found.")
            for row in result:
                print(f"#{row['id']} @{row['username']} [{row['category']}] — {row['status']}")
        elif args.command == "show":
            print(json.dumps(get_case(db, args.id), ensure_ascii=False, indent=2))
        elif args.command == "evidence":
            require_case(db, args.id)
            url = check_url(args.url)
            description = args.description.strip()
            if not description:
                raise ValueError("Evidence description cannot be empty.")
            db.execute(
                "INSERT INTO evidence (case_id, url, description, created_at) "
                "VALUES (?, ?, ?, ?)",
                (args.id, url, description, timestamp()),
            )
            db.execute(
                "UPDATE cases SET updated_at = ? WHERE id = ?", (timestamp(), args.id)
            )
            db.commit()
            print(f"Added evidence to case #{args.id}.")
        elif args.command == "status":
            require_case(db, args.id)
            db.execute(
                "UPDATE cases SET status = ?, updated_at = ? WHERE id = ?",
                (args.value, timestamp(), args.id),
            )
            db.commit()
            print(f"Case #{args.id} marked {args.value}.")
        elif args.command == "stats":
            counts = Counter(
                {row["status"]: row["count"] for row in db.execute(
                    "SELECT status, COUNT(*) AS count FROM cases GROUP BY status"
                )}
            )
            print("Cases:", sum(counts.values()))
            for status in STATUSES:
                print(f"  {status}: {counts[status]}")
        elif args.command == "export":
            output = Path(args.output).expanduser()
            if output.resolve() == Path(args.db).expanduser().resolve():
                raise ValueError("Export path cannot overwrite the database.")
            cases = [
                get_case(db, row["id"])
                for row in db.execute("SELECT id FROM cases ORDER BY id")
            ]
            # Criação exclusiva: não sobrescrever arquivos preexistentes.
            # O modo privado é aplicado na abertura, não depois da escrita.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            with os.fdopen(os.open(output, flags, 0o600), "w", encoding="utf-8") as handle:
                json.dump(
                    {"exported_at": timestamp(), "cases": cases},
                    handle, ensure_ascii=False, indent=2,
                )
                handle.write("\n")
            print(f"Exported {len(cases)} case(s) to {output}.")
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
