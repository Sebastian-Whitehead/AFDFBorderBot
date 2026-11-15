"""Copy users and active LOAs from a local bot DB into a Supabase-shaped DB (idempotent, with --dry-run).

Usage: python migration/migrate_to_supabase.py --source-url <asyncpg url> --target-url <asyncpg url> [--dry-run] [--allow-remote]
"""
import argparse
import asyncio
import json
import sys
import threading
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.loa_functions import LOAManager  # noqa: E402
from database.rank_codes import level_to_code  # noqa: E402

ORG = "AFDF-Para Raiders"
LOCAL_HOSTS = ("localhost", "127.0.0.1")


class Skip(Exception):
    """Abort the current savepoint and record the row as skipped."""


def _utc(dt):
    # Local columns are naive timestamps; treat them as UTC.
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _json(v):
    return json.loads(v) if isinstance(v, str) else v


async def _migrate_user(conn, u, rep):
    steam_s = (u.steam_id or "").strip()
    if not (steam_s.isascii() and steam_s.isdigit()):
        raise Skip("non-numeric steam_id")
    steam = int(steam_s)
    try:
        code = level_to_code(u.rank)
    except (KeyError, TypeError):
        raise Skip(f"unknown rank {u.rank}")
    d = (u.discord_id or "").strip()
    discord = int(d) if d.isascii() and d.isdigit() else None

    existing = (await conn.execute(
        text("SELECT id, discord_id FROM public.identities_player WHERE steam_id = :s"), {"s": steam}
    )).first()
    if discord is not None:
        other = (await conn.execute(
            text("SELECT id FROM public.identities_player WHERE discord_id = :d AND steam_id IS DISTINCT FROM :s"),
            {"d": discord, "s": steam},
        )).first()
        if other:
            raise Skip(f"discord_id used by identity {other.id}")

    await conn.execute(
        text("SELECT public.fab_ensure_player_account(:name, :steam, :discord)"),
        {"name": u.name, "steam": steam, "discord": None if existing else discord},
    )
    ident = (await conn.execute(
        text("SELECT id, discord_id FROM public.identities_player WHERE steam_id = :s"), {"s": steam}
    )).one()
    if existing:
        if discord is not None:
            if ident.discord_id is None:
                await conn.execute(text("UPDATE public.identities_player SET discord_id = :d WHERE id = :id"),
                                   {"d": discord, "id": ident.id})
            elif ident.discord_id != discord:
                rep["warnings"].append(f"discord conflict: local id {u.id} (kept {ident.discord_id}, local {discord})")
        rep["adopted"] += 1
    else:
        if discord is not None and ident.discord_id is None:
            await conn.execute(text("UPDATE public.identities_player SET discord_id = :d WHERE id = :id"),
                               {"d": discord, "id": ident.id})
        rep["created"] += 1

    if u.joined_at is not None:
        await conn.execute(
            text("UPDATE public.identities_player SET created_at = LEAST(created_at, CAST(:j AS timestamptz)) WHERE id = :id"),
            {"j": _utc(u.joined_at), "id": ident.id},
        )

    sr_id = (await conn.execute(text("""
        SELECT sr.id FROM military.service_records sr
        JOIN public.identities_organizations o ON o.id = sr.organization_id
        WHERE sr.player_identity_id = :p AND o.name = :org"""), {"p": ident.id, "org": ORG})).scalar_one_or_none()
    if sr_id is None:
        sr_id = (await conn.execute(text("""
            INSERT INTO military.service_records (player_identity_id, organization_id, current_rank, service_status)
            SELECT :p, o.id, :code, 'active' FROM public.identities_organizations o WHERE o.name = :org
            RETURNING id"""), {"p": ident.id, "code": code, "org": ORG})).scalar_one()
    else:
        rep["record_existed"] += 1

    if u.enlisted_at is not None:
        has = (await conn.execute(text("""
            SELECT 1 FROM military.service_events
            WHERE service_record_id = :sr AND event_type IN ('enlisted', 'reenlisted') LIMIT 1"""),
            {"sr": sr_id})).first()
        if not has:
            await conn.execute(text("""
                INSERT INTO military.service_events (service_record_id, event_type, rank, occured_at)
                VALUES (:sr, 'enlisted', :code, CAST(:t AS timestamptz))"""),
                {"sr": sr_id, "code": code, "t": _utc(u.enlisted_at)})

    # Money is intentionally not migrated.
    new = {}
    if u.notes is not None:
        new["notes"] = u.notes
    if u.achievements is not None:
        new["achievements"] = list(u.achievements)
    if u.deaths is not None:
        new["deaths"] = u.deaths
    if u.last_death is not None:
        new["last_death"] = u.last_death.isoformat()
    for k in ("reprimands", "extra_data"):
        v = _json(getattr(u, k))
        if v is not None:
            new[k] = v
    if new:  # existing keys win
        await conn.execute(
            text("""UPDATE public.identities_player
                    SET details = CAST(:new AS jsonb) || coalesce(details, '{}'::jsonb) WHERE id = :id"""),
            {"new": json.dumps(new), "id": ident.id},
        )


async def _migrate_loa(conn, l, rep):
    end = await LOAManager.parse_end_date(l.end_date)
    if end is None:
        raise Skip(f"unparseable end_date '{l.end_date}'")
    d = (l.discord_id or "").strip()
    sr_id = None
    if d.isascii() and d.isdigit():
        sr_id = (await conn.execute(text("""
            SELECT sr.id FROM military.service_records sr
            JOIN public.identities_player p ON p.id = sr.player_identity_id
            JOIN public.identities_organizations o ON o.id = sr.organization_id
            WHERE p.discord_id = :d AND o.name = :org"""), {"d": int(d), "org": ORG})).scalar_one_or_none()
    if sr_id is None:
        raise Skip("no service record")
    created = _utc(l.submitted_at)
    if created is not None and (await conn.execute(text("""
            SELECT 1 FROM military.leave_requests WHERE service_record_id = :sr AND created_at = CAST(:c AS timestamptz)"""),
            {"sr": sr_id, "c": created})).first():
        rep["loa_already"] += 1
        return
    status = "expired" if end < date.today() else "active"
    try:
        # LEAST: past end dates must not violate end_date >= start_date.
        await conn.execute(text("""
            INSERT INTO military.leave_requests
                (service_record_id, start_date, end_date, reason, status, submitted_by, created_at, updated_at)
            VALUES (:sr, LEAST(CAST(:s AS date), CAST(:e AS date)), CAST(:e AS date), :r, :st, :u,
                    coalesce(CAST(:c AS timestamptz), now()),
                    coalesce(CAST(:m AS timestamptz), CAST(:c AS timestamptz), now()))"""),
            {"sr": sr_id, "s": l.start_date, "e": end, "r": l.reason, "st": status, "u": l.username,
             "c": created, "m": _utc(l.last_modified)})
    except IntegrityError as e:
        if status == "active" and "leave_requests_one_active" in str(e):
            raise Skip("another active LOA exists")
        raise
    rep["loa_expired" if status == "expired" else "loa_migrated"] += 1


async def _run(args):
    rep = {"created": 0, "adopted": 0, "record_existed": 0, "warnings": [], "skipped": [],
           "loa_migrated": 0, "loa_expired": 0, "loa_already": 0, "loa_skipped": []}
    src = create_async_engine(args.source_url, poolclass=NullPool)
    tgt = create_async_engine(args.target_url, poolclass=NullPool)
    try:
        async with src.connect() as s:
            users = (await s.execute(text("SELECT * FROM users ORDER BY id"))).all()
            loas = (await s.execute(text("SELECT * FROM loa_requests WHERE status = 'active' ORDER BY id"))).all()
        async with tgt.connect() as conn:
            trans = await conn.begin()
            try:
                for u in users:
                    try:
                        async with conn.begin_nested():
                            await _migrate_user(conn, u, rep)
                    except Skip as e:
                        rep["skipped"].append(f"local id {u.id}: {e}")
                    except Exception as e:
                        rep["skipped"].append(f"local id {u.id}: error {type(e).__name__}: {e}")
                for l in loas:
                    try:
                        async with conn.begin_nested():
                            await _migrate_loa(conn, l, rep)
                    except Skip as e:
                        rep["loa_skipped"].append(f"local id {l.id}: {e}")
                    except Exception as e:
                        rep["loa_skipped"].append(f"local id {l.id}: error {type(e).__name__}: {e}")
            except BaseException:
                await trans.rollback()
                raise
            if args.dry_run:
                await trans.rollback()
            else:
                await trans.commit()
    finally:
        await src.dispose()
        await tgt.dispose()
    return rep


def _report(rep, dry_run):
    out = [f"Users created: {rep['created']}", f"Users adopted: {rep['adopted']}",
           f"Service records already existed: {rep['record_existed']}",
           f"Users skipped: {len(rep['skipped'])}"]
    out += [f"  {r}" for r in rep["skipped"]]
    out.append(f"Warnings: {len(rep['warnings'])}")
    out += [f"  {w}" for w in rep["warnings"]]
    out += [f"LOAs migrated: {rep['loa_migrated']}", f"LOAs expired: {rep['loa_expired']}",
            f"LOAs already migrated: {rep['loa_already']}", f"LOAs skipped: {len(rep['loa_skipped'])}"]
    out += [f"  {r}" for r in rep["loa_skipped"]]
    if dry_run:
        out.append("DRY RUN – rolled back")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-url", required=True)
    p.add_argument("--target-url", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--allow-remote", action="store_true")
    args = p.parse_args(argv)

    host = make_url(args.target_url).host
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"Refusing to migrate to remote host '{host}' without --allow-remote", file=sys.stderr)
        return 2

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        rep = asyncio.run(_run(args))
    else:  # called from inside a running loop (tests): use a private thread
        box = []
        t = threading.Thread(target=lambda: box.append(asyncio.run(_run(args))))
        t.start()
        t.join()
        rep = box[0]

    text_out = _report(rep, args.dry_run)
    print(text_out)
    d = ROOT / "migration" / "backup"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"migration-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt").write_text(text_out + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
