#!/usr/bin/env python3
"""One-time migration of the local CloudKrafts SQLite database to Supabase PostgreSQL."""
import os, sys, sqlite3
import psycopg
from pathlib import Path
from psycopg.rows import tuple_row
import server

def main():
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("Set DATABASE_URL to your Supabase PostgreSQL connection string first.")
    if len(os.environ.get("APP_SECRET", "")) < 32:
        raise SystemExit("Set APP_SECRET to the same secret configured on Render (at least 32 characters).")
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "local-data.sqlite3")
    if not source.exists():
        raise SystemExit(f"SQLite file not found: {source.resolve()}")
    old = sqlite3.connect(source)
    old.row_factory = sqlite3.Row
    vendors = old.execute("SELECT id,name,contact,secret,password_local FROM vendors ORDER BY id").fetchall()
    qcols = [r[1] for r in old.execute("PRAGMA table_info(qr)").fetchall()]
    needed = ["id","vendor_id","status","shop","url","pin","batch_id","downloaded_at","created","updated"]
    select = ",".join(c if c in qcols else "'' AS "+c for c in needed)
    qrs = old.execute(f"SELECT {select} FROM qr ORDER BY id").fetchall()
    audit_exists = old.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit'").fetchone()
    audits = old.execute("SELECT id,qr,action,at FROM audit ORDER BY id").fetchall() if audit_exists else []
    server.init()
    with psycopg.connect(os.environ["DATABASE_URL"]) as pg:
        with pg.cursor() as cur:
            cur.execute("SELECT (SELECT COUNT(*) FROM vendors)+(SELECT COUNT(*) FROM qr)")
            if cur.fetchone()[0]:
                raise SystemExit("Target database is not empty. Stop to avoid duplicating or overwriting production records.")
            cur.executemany(
                "INSERT INTO vendors(id,name,contact,secret,password_local) VALUES(%s,%s,%s,%s,%s)",
                [(v["id"],v["name"],v["contact"],v["secret"],server.protect_password(v["password_local"] or "")) for v in vendors]
            )
            cur.executemany(
                """INSERT INTO qr(id,vendor_id,status,shop,url,pin,batch_id,downloaded_at,created,updated)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                [tuple(q[c] if q[c] != "" else (None if c in ("created","updated","downloaded_at") else "") for c in needed) for q in qrs]
            )
            if audits:
                cur.executemany("INSERT INTO audit(id,qr,action,at) VALUES(%s,%s,%s,%s)",
                                [(a["id"],a["qr"],a["action"],a["at"] or None) for a in audits])
            cur.execute("SELECT setval(pg_get_serial_sequence('vendors','id'), GREATEST(COALESCE((SELECT MAX(id) FROM vendors),1),1), true)")
            cur.execute("SELECT setval(pg_get_serial_sequence('audit','id'), GREATEST(COALESCE((SELECT MAX(id) FROM audit),1),1), true)")
    old.close()
    print(f"Migration complete: {len(vendors)} vendors, {len(qrs)} QR records, {len(audits)} audit events.")
    print("Verify counts in Supabase before switching live traffic.")

if __name__ == "__main__":
    main()
