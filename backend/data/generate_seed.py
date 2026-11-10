"""Deterministic, FICTIONAL Oil & Gas mechanical-integrity demo records.

No equipment limits or engineering acceptance criteria are provided. Never use
this data for actual plant operations, maintenance or fitness-for-service.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(204310120)
out = Path(__file__).resolve().parent
base = date(2026, 6, 1)
assets, inspections, maintenance, incidents = [], [], [], []

classes = [
    (
        "Pump",
        "P",
        range(201, 221),
        [
            "Crude transfer pump",
            "Produced-water circulation pump",
            "Condensate transfer pump",
            "Cooling-water circulation pump",
        ],
        ["Process Area A", "Tank Farm", "Utilities"],
        "ROT-EQ",
    ),
    (
        "Valve",
        "CV",
        range(301, 321),
        [
            "Flow-control valve",
            "Pressure-control valve",
            "Level-control valve",
            "Isolation/control valve",
        ],
        ["Separation Train", "Process Area B", "Utilities"],
        "VLV-EQ",
    ),
    (
        "Pressure Vessel",
        "PV",
        range(101, 121),
        ["Three-phase separator", "Knockout drum", "Filter vessel", "Surge vessel"],
        ["Separation Train", "Gas Handling", "Utilities"],
        "STATIC-EQ",
    ),
]
for category, prefix, numbers, names, units, design_prefix in classes:
    for n in numbers:
        asset_id = f"{prefix}-{n}"
        status = (
            "Review"
            if (n % 7 == 0 or asset_id in ("P-204", "CV-310", "PV-120"))
            else ("Hold" if n % 13 == 0 else "Normal")
        )
        asset = dict(
            id=asset_id,
            name=names[n % len(names)],
            category=category,
            service={
                "Pump": "Liquid transfer",
                "Valve": "Flow regulation",
                "Pressure Vessel": "Process separation",
            }[category],
            unit=units[n % len(units)],
            location=f"{units[n % len(units)]} / Bay {n % 5 + 1}",
            status=status,
            criticality="High" if n % 4 == 0 else "Medium",
            installed_at=str(date(2018 + (n % 7), 1 + (n % 11), 1 + (n % 25))),
            design_reference=f"{design_prefix}-{n:03}",
            description=f"Synthetic {category.lower()} asset in a fictitious upstream/downstream processing facility. No design or operating limits are supplied.",
        )
        assets.append(asset)
        for j in range(3):
            if category == "Pump":
                label, unit = "Vibration velocity", "mm/s RMS"
                reading = round(
                    rng.uniform(2.0, 6.8) + (1.6 if asset_id == "P-204" and j == 2 else 0), 2
                )
                note = (
                    "Vibration trend warrants engineering review; no acceptance threshold encoded."
                    if j == 2 and status != "Normal"
                    else "Routine vibration observation recorded; trend against approved site baseline."
                )
            elif category == "Valve":
                label, unit = "Actuator travel deviation", "%"
                reading = round(
                    rng.uniform(0.3, 4.6) + (1.1 if asset_id == "CV-310" and j == 2 else 0), 2
                )
                note = (
                    "Possible actuator response discrepancy; requires site engineering evaluation."
                    if j == 2 and status != "Normal"
                    else "Actuator functional observation recorded, acceptance criteria not provided."
                )
            else:
                label, unit = "UT thickness reading", "mm"
                reading = round(
                    rng.uniform(10.0, 16.8) - (1.2 if asset_id == "PV-120" and j == 2 else 0), 2
                )
                note = (
                    "Thickness trend requires qualified corrosion review; minimum allowable thickness unknown."
                    if j == 2 and status != "Normal"
                    else "Ultrasonic thickness reading for trending; no remaining-life claim."
                )
            outcome = (
                "Review"
                if (j == 2 and status != "Normal")
                or (asset_id in ("P-204", "CV-310", "PV-120") and j == 1)
                else "Pass"
            )
            if status == "Hold" and j == 2:
                outcome = "Hold"
            inspections.append(
                dict(
                    id=f"INSP-{asset_id}-{j + 1:02}",
                    asset_id=asset_id,
                    inspected_at=str(base + timedelta(days=(n % 40) + j * 28)),
                    inspection_type={
                        "Pump": "Vibration and seal observation",
                        "Valve": "Actuator functional check",
                        "Pressure Vessel": "UT thickness survey",
                    }[category],
                    metric=label,
                    reading=reading,
                    unit=unit,
                    outcome=outcome,
                    inspector=f"Training Inspector {1 + n % 8}",
                    notes=note,
                )
            )
        for j in range(2):
            if category == "Pump":
                task = ["Lubrication and condition review", "Seal and vibration trend review"][j]
            elif category == "Valve":
                task = [
                    "Valve actuator condition review",
                    "Instrument air and positioner record review",
                ][j]
            else:
                task = ["External condition walkdown", "Historical thickness map review"][j]
            maintenance.append(
                dict(
                    id=f"WO-{asset_id}-{j + 1:02}",
                    asset_id=asset_id,
                    performed_at=str(base + timedelta(days=(n % 37) + j * 32 + 2)),
                    work_type=task,
                    status="Open" if j == 1 and status != "Normal" else "Completed",
                    description=f"{task} recorded for synthetic {asset_id}.",
                    action_taken="Inspection evidence filed; no field action asserted."
                    if j == 0
                    else "Engineering follow-up requested; actual work not represented.",
                    next_step="Check approved site procedure and involve authorized personnel."
                    if j == 1
                    else "Continue approved inspection program.",
                )
            )

# Realistic relationships: a record refers to an existing asset; timestamps are historical.
anchors = [
    (
        "INC-007",
        "P-204",
        "High",
        "Open",
        "Elevated vibration trend and intermittent mechanical-seal leakage observation",
        "Request vibration trend validation, seal condition review and approved isolation assessment.",
    ),
    (
        "INC-010",
        "CV-310",
        "Medium",
        "Under review",
        "Control valve response lag and inconsistent actuator position feedback",
        "Correlate positioner diagnostic records with functional test evidence.",
    ),
    (
        "INC-012",
        "PV-120",
        "High",
        "Open",
        "Localized wall-thickness trend and external corrosion indication",
        "Review thickness mapping, corrosion rate assumptions and qualified inspection disposition.",
    ),
]
for incident_id, aid, sev, status, issue, followup in anchors:
    incidents.append(
        dict(
            id=incident_id,
            asset_id=aid,
            severity=sev,
            status=status,
            issue=issue,
            recorded_at=str(base + timedelta(days=90)),
            follow_up=followup,
        )
    )
extras = ["P-207", "P-216", "CV-303", "CV-316", "PV-103", "PV-112", "P-213", "CV-307", "PV-109"]
for k, aid in enumerate(extras, 1):
    inc_id = f"INC-{20 + k:03}"
    issues = (
        "Equipment condition anomaly identified during routine review"
        if aid.startswith("P-")
        else "Functional test discrepancy documented for engineering review"
        if aid.startswith("CV-")
        else "Inspection observation requiring corrosion engineering follow-up"
    )
    incidents.append(
        dict(
            id=inc_id,
            asset_id=aid,
            severity="Medium",
            status="Under review",
            issue=issues,
            recorded_at=str(base + timedelta(days=60 + k * 3)),
            follow_up="Evaluate evidence against the approved asset-specific inspection plan.",
        )
    )

# Demonstrate historical status-to-incident consistency for the three named examples.
for a in assets:
    if a["id"] in ("P-204", "CV-310", "PV-120"):
        a["status"] = "Review"

payload = {
    "assets": assets,
    "inspections": inspections,
    "maintenance": maintenance,
    "incidents": incidents,
}
(out / "asset_integrity_seed.json").write_text(json.dumps(payload, indent=2) + "\n")
print({k: len(v) for k, v in payload.items()})
