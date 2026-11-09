"""Synthetic oil-and-gas equipment records and explicitly approved demo reports.

All asset history tools are read-only. Report writes are separate HTTP actions.
This is not a CMMS, safety system or fitness-for-service evaluator.
"""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from .config import DATABASE_PATH, DATA_DIR

_LOCK = threading.RLock()
_TABLES = ('assets','inspections','maintenance','incidents','reports')


def connect():
    conn=sqlite3.connect(DATABASE_PATH,timeout=10,check_same_thread=False)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def initialize():
    """Create relational schema and seed consistent, fictional records once."""
    with _LOCK, connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS assets (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
          service TEXT NOT NULL, unit TEXT NOT NULL, location TEXT NOT NULL,
          status TEXT NOT NULL, criticality TEXT NOT NULL, installed_at TEXT NOT NULL,
          design_reference TEXT NOT NULL, description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inspections (
          id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
          inspected_at TEXT NOT NULL, inspection_type TEXT NOT NULL,
          metric TEXT NOT NULL, reading REAL NOT NULL, unit TEXT NOT NULL,
          outcome TEXT NOT NULL, inspector TEXT NOT NULL, notes TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maintenance (
          id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
          performed_at TEXT NOT NULL, work_type TEXT NOT NULL,
          status TEXT NOT NULL, description TEXT NOT NULL,
          action_taken TEXT NOT NULL, next_step TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS incidents (
          id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
          severity TEXT NOT NULL, status TEXT NOT NULL,
          issue TEXT NOT NULL, recorded_at TEXT NOT NULL, follow_up TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reports (
          id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
          status TEXT NOT NULL CHECK(status IN ('pending','approved')),
          summary TEXT NOT NULL, created_at TEXT NOT NULL, approved_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_inspections_asset ON inspections(asset_id);
        CREATE INDEX IF NOT EXISTS idx_maintenance_asset ON maintenance(asset_id);
        CREATE INDEX IF NOT EXISTS idx_incidents_asset ON incidents(asset_id);
        ''')
        if con.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 0:
            data=json.loads((DATA_DIR/'asset_integrity_seed.json').read_text())
            for table in ('assets','inspections','maintenance','incidents'):
                rows=data[table]
                if rows:
                    keys=list(rows[0]); columns=','.join(keys)
                    values=','.join('?' for _ in keys)
                    con.executemany(f'INSERT INTO {table}({columns}) VALUES ({values})',
                                    [[row[k] for k in keys] for row in rows])


def _all(sql,parameters=()):
    with connect() as con:
        return [dict(row) for row in con.execute(sql,parameters).fetchall()]


def list_assets(search='',limit=100):
    query=f'%{search[:60]}%'
    return _all('SELECT * FROM assets WHERE id LIKE ? OR name LIKE ? OR category LIKE ? OR unit LIKE ? ORDER BY id LIMIT ?',
                (query,query,query,query,min(max(limit,1),100)))


def get_asset(asset_id):
    matches=_all('SELECT * FROM assets WHERE id=?',(asset_id.upper(),))
    return matches[0] if matches else None


def get_inspections(asset_id):
    return _all('SELECT * FROM inspections WHERE asset_id=? ORDER BY inspected_at DESC LIMIT 100',(asset_id.upper(),))


def get_maintenance(asset_id):
    return _all('SELECT * FROM maintenance WHERE asset_id=? ORDER BY performed_at DESC LIMIT 100',(asset_id.upper(),))


def get_incidents(asset_id):
    return _all('SELECT * FROM incidents WHERE asset_id=? ORDER BY recorded_at DESC LIMIT 100',(asset_id.upper(),))


def counts():
    with connect() as con:
        return {table:con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in _TABLES}


def create_draft(asset_id):
    """Deterministic draft from database facts; the LLM cannot call this tool."""
    asset_id=asset_id.upper()
    asset=get_asset(asset_id)
    if not asset:return None
    checks=get_inspections(asset_id)
    work=get_maintenance(asset_id)
    incidents=get_incidents(asset_id)
    flags=[r for r in checks if r['outcome']!='Pass']
    open_work=[r for r in work if r['status']!='Completed']
    summary=(f'SYNTHETIC MECHANICAL INTEGRITY REVIEW — {asset_id}\n'
             f'Asset: {asset["name"]} ({asset["category"]})\n'
             f'Location: {asset["location"]}; status: {asset["status"]}.\n'
             f'Inspections: {len(checks)}; flagged: {len(flags)}.\n'
             f'Maintenance records: {len(work)}; open follow-ups: {len(open_work)}.\n'
             f'Incidents: {len(incidents)}.\n'
             f'Observed incident evidence: {"; ".join(x["id"]+": "+x["issue"] for x in incidents[:3]) or "None recorded"}.\n'
             f'Open work orders: {", ".join(x["id"] for x in open_work) or "None recorded"}.\n'
             'Suggested next step: compare evidence against approved site SOPs, check units and calibration, '
             'and ask qualified asset integrity personnel to review findings. No operational limit or '
             'fitness-for-service assessment is supplied. This demo approval has no operational effect.')
    rid='RPT-'+uuid.uuid4().hex[:8].upper()
    now=datetime.now(timezone.utc).isoformat()
    with _LOCK,connect() as con:
        con.execute('INSERT INTO reports(id,asset_id,status,summary,created_at) VALUES (?,?,?,?,?)',
                    (rid,asset_id,'pending',summary,now))
    return get_report(rid)


def get_report(report_id):
    rows=_all('SELECT * FROM reports WHERE id=?',(report_id,))
    return rows[0] if rows else None


def list_reports():
    return _all('SELECT * FROM reports ORDER BY created_at DESC LIMIT 100')


def approve_report(report_id):
    with _LOCK,connect() as con:
        con.execute("UPDATE reports SET status='approved', approved_at=? WHERE id=? AND status='pending'",
                    (datetime.now(timezone.utc).isoformat(),report_id))
    return get_report(report_id)
