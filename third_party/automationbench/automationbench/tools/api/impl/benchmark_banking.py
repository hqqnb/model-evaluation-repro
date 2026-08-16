# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""API adapters for the deterministic banking benchmark service."""

from __future__ import annotations

import json
from typing import Any

from automationbench.schema.world import WorldState
from automationbench.tools.zapier.banking import (
    banking_find_customer,
    banking_get_transaction,
    banking_list_accounts,
    banking_request_limit_increase,
    banking_request_transfer_review,
    banking_search_policy,
    banking_transfer_to_human,
    banking_verify_identity,
)


def _payload(value: str) -> dict[str, Any]:
    return json.loads(value)


def banking_customer_get(world: WorldState, customer_id: str, **_: Any) -> str:
    return banking_find_customer(world, customer_id=customer_id)


def banking_accounts_list(world: WorldState, customer_id: str = "", **_: Any) -> str:
    return banking_list_accounts(world, customer_id=customer_id)


def banking_transaction_get(world: WorldState, transaction_id: str, **_: Any) -> str:
    return banking_get_transaction(world, transaction_id=transaction_id)


def banking_policy_search(world: WorldState, q: str = "", **_: Any) -> str:
    return banking_search_policy(world, query=q)


def banking_verification_create(world: WorldState, body: dict[str, Any]) -> str:
    return banking_verify_identity(
        world,
        customer_id=str(body.get("customerId", "")),
        method=str(body.get("method", "")),
        value=str(body.get("value", "")),
    )


def banking_transfer_review_create(
    world: WorldState, transaction_id: str, body: dict[str, Any]
) -> str:
    return banking_request_transfer_review(
        world, transaction_id=transaction_id, reason=str(body.get("reason", ""))
    )


def banking_limit_request_create(
    world: WorldState, account_id: str, body: dict[str, Any]
) -> str:
    return banking_request_limit_increase(
        world,
        account_id=account_id,
        requested_limit=float(body.get("requestedLimit", 0)),
        reason=str(body.get("reason", "")),
    )


def banking_handoff_create(world: WorldState, body: dict[str, Any]) -> str:
    return banking_transfer_to_human(
        world,
        reason=str(body.get("reason", "")),
        summary=str(body.get("summary", "")),
    )
