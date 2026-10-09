"""Preserve legitimately supplied files and check their bytes locally."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat
import uuid

from instaguard import check_url, require_case, timestamp

MAX_BYTES = 25 * 1024 * 1024


def observation_time(value):
    if not value:
        return None
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("Observation time must include a timezone.")
    if date > datetime.now(timezone.utc):
        raise ValueError("Observation time cannot be in the future.")
    return date.astimezone(timezone.utc).isoformat(timespec="seconds")


def digest_file(path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("Evidence must be a regular file.")
        digest, size = hashlib.sha256(), 0
        while True:
            chunk = source.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("Evidence exceeds 25 MiB.")
            digest.update(chunk)
    return digest.hexdigest(), size


def register_evidence(db, case_id, url, description, file=None, observed_at=None, collector=""):
    require_case(db, case_id)
    url = check_url(url)
    description, collector = description.strip(), collector.strip()
    if not description or len(description) > 2000 or len(collector) > 120:
        raise ValueError("Description or collector label is invalid.")
    observed_at = observation_time(observed_at)
    artifact, sha, size = None, None, None
    if file:
        source = Path(file).expanduser()
        if source.is_symlink():
            raise ValueError("Symbolic links cannot be evidence files.")
        database = db.execute("PRAGMA database_list").fetchone()[2]
        if not database:
            raise ValueError("File preservation requires an on-disk database.")
        if source.resolve() == Path(database).resolve():
            raise ValueError("Do not attach the case database as evidence.")
        root = Path(database).parent / "evidence-files"
        if root.is_symlink():
            raise ValueError("Evidence directory cannot be a symbolic link.")
        root.mkdir(mode=0o700, exist_ok=True)
        root.chmod(0o700)
        artifact = root / (uuid.uuid4().hex + ".bin")
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            with os.fdopen(os.open(source, flags), "rb") as incoming:
                if not stat.S_ISREG(os.fstat(incoming.fileno()).st_mode):
                    raise ValueError("Evidence must be a regular file.")
                with os.fdopen(os.open(artifact, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as out:
                    size, digest = 0, hashlib.sha256()
                    while True:
                        chunk = incoming.read(65536)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ValueError("Evidence exceeds 25 MiB.")
                        out.write(chunk)
                        digest.update(chunk)
                    out.flush()
                    os.fsync(out.fileno())
                    sha = digest.hexdigest()
        except Exception:
            artifact.unlink(missing_ok=True)
            raise
    now = timestamp()
    try:
        with db:
            cur = db.execute(
                "INSERT INTO evidence(case_id,url,description,created_at,observed_at,collector,method,artifact_path,sha256,size_bytes) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (case_id, url, description, now, observed_at, collector,
                 "operator_supplied_file" if file else "operator_supplied_url",
                 str(artifact) if artifact else None, sha, size),
            )
            db.execute("UPDATE cases SET updated_at=? WHERE id=?", (now, case_id))
        return cur.lastrowid
    except Exception:
        if artifact:
            artifact.unlink(missing_ok=True)
        raise


def verify_evidence(item):
    """Hash agreement proves stored bytes only, never authorship or truth."""
    result = {"evidence_id": item.get("id"), "status": "unverified",
              "content_authenticity": "not_established", "sha256": item.get("sha256")}
    if not item.get("artifact_path"):
        result["detail"] = "URL only; no preserved file available."
        return result
    path = Path(item["artifact_path"])
    try:
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("Symbolic link refused.")
        sha, size = digest_file(path)
        result["status"] = "verified_bytes" if (sha == item.get("sha256") and size == item.get("size_bytes")) else "mismatch"
        result["detail"] = "Compared preserved bytes with registered SHA-256 and size."
    except (OSError, ValueError):
        result["status"] = "unavailable"
        result["detail"] = "Preserved file could not be checked."
    return result
