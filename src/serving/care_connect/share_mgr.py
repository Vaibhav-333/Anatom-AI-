"""Token-based report sharing with expiry and view tracking."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone


BASE_URL = "https://anatom.ai"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _utc_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


async def create_share_token(db, report_id: str, expiry_hours: int) -> dict:
    """Create a new share token for a report."""
    token = secrets.token_urlsafe(32)
    expires_at = _now_utc() + timedelta(hours=expiry_hours)
    expires_str = _utc_str(expires_at)

    await db.execute(
        """INSERT INTO shared_reports (token, report_id, expires_at)
           VALUES (?, ?, ?)""",
        (token, report_id, expires_str),
    )
    await db.commit()

    return {
        "token": token,
        "share_url": f"{BASE_URL}/share/{token}",
        "expires_at": expires_str,
        "view_count": 0,
    }


async def get_share_record(db, token: str) -> dict | None:
    """Fetch share record; returns None if not found, revoked, or expired."""
    async with db.execute(
        "SELECT * FROM shared_reports WHERE token = ?", (token,)
    ) as cur:
        row = await cur.fetchone()

    if not row:
        return None
    if row["is_revoked"]:
        return None

    expires_at = datetime.fromisoformat(row["expires_at"]).replace(tzinfo=timezone.utc)
    if _now_utc() > expires_at:
        return None

    return dict(row)


async def record_view(db, token: str, viewer_ip: str | None = None) -> None:
    """Increment view counter and log the view."""
    now = _utc_str(_now_utc())
    await db.execute(
        "UPDATE shared_reports SET view_count = view_count + 1, last_viewed_at = ? WHERE token = ?",
        (now, token),
    )
    await db.execute(
        "INSERT INTO report_views (token, viewed_at, viewer_ip) VALUES (?, ?, ?)",
        (token, now, viewer_ip),
    )
    await db.commit()


async def revoke_token(db, token: str) -> bool:
    """Revoke a share token. Returns True if found and revoked."""
    async with db.execute(
        "SELECT token FROM shared_reports WHERE token = ?", (token,)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return False
    await db.execute(
        "UPDATE shared_reports SET is_revoked = 1 WHERE token = ?", (token,)
    )
    await db.commit()
    return True


async def get_share_info(db, report_id: str) -> list[dict]:
    """Get all active share links for a report."""
    async with db.execute(
        "SELECT * FROM shared_reports WHERE report_id = ? AND is_revoked = 0 ORDER BY created_at DESC",
        (report_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
