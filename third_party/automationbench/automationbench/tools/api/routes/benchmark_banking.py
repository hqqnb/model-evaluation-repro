# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""REST-style routes for the benchmark banking service."""

from automationbench.tools.api.impl.benchmark_banking import (
    banking_accounts_list,
    banking_customer_get,
    banking_handoff_create,
    banking_limit_request_create,
    banking_policy_search,
    banking_transaction_get,
    banking_transfer_review_create,
    banking_verification_create,
)
from automationbench.utils.routing import make_router


_ROUTES = [
    ("GET", r"banking/v1/customers/([^/]+)$", "customer_get"),
    ("GET", r"banking/v1/accounts$", "accounts_list"),
    ("GET", r"banking/v1/transactions/([^/]+)$", "transaction_get"),
    ("GET", r"banking/v1/policies/search$", "policy_search"),
    ("POST", r"banking/v1/verifications$", "verification_create"),
    ("POST", r"banking/v1/transfers/([^/]+)/review$", "transfer_review_create"),
    ("POST", r"banking/v1/accounts/([^/]+)/limit-requests$", "limit_request_create"),
    ("POST", r"banking/v1/handoffs$", "handoff_create"),
]

_HANDLERS = {
    "customer_get": lambda w, ids, p, b: banking_customer_get(w, ids[0]),
    "accounts_list": lambda w, ids, p, b: banking_accounts_list(
        w, customer_id=p.get("customerId", "")
    ),
    "transaction_get": lambda w, ids, p, b: banking_transaction_get(w, ids[0]),
    "policy_search": lambda w, ids, p, b: banking_policy_search(w, q=p.get("q", "")),
    "verification_create": lambda w, ids, p, b: banking_verification_create(w, b),
    "transfer_review_create": lambda w, ids, p, b: banking_transfer_review_create(w, ids[0], b),
    "limit_request_create": lambda w, ids, p, b: banking_limit_request_create(w, ids[0], b),
    "handoff_create": lambda w, ids, p, b: banking_handoff_create(w, b),
}

route_banking = make_router(_ROUTES, _HANDLERS)

# Keep the exported name aligned with the WorldState field for service gating.
route_benchmark_banking = route_banking
