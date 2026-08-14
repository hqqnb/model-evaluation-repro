"""仅缺陷3：金额用精确相等比较，拒绝合理浮点误差。"""

import re


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_order(order: dict) -> list[str]:
    errs = []
    oid = order.get("id")
    if not isinstance(oid, str) or not oid:
        errs.append("id")

    amount = order.get("amount")
    if not isinstance(amount, (int, float)) or not (0 < amount <= 10000):
        errs.append("amount")

    cur = order.get("currency")
    if not isinstance(cur, str) or re.fullmatch(r"[A-Z]{3}", cur) is None:
        errs.append("currency")

    email = order.get("email")
    if not isinstance(email, str) or EMAIL_RE.fullmatch(email) is None:
        errs.append("email")

    items = order.get("items")
    if not isinstance(items, list) or not (1 <= len(items) <= 50):
        errs.append("items")
        return errs

    total = 0.0
    for it in items:
        if not isinstance(it, dict):
            errs.append("item")
            continue
        name = it.get("name")
        if not isinstance(name, str) or not name or len(name) > 100:
            errs.append("item.name")
        qty = it.get("qty")
        if not isinstance(qty, int) or not (1 <= qty <= 99):
            errs.append("item.qty")
        up = it.get("unit_price")
        if not isinstance(up, (int, float)) or up <= 0:
            errs.append("item.unit_price")
        if isinstance(qty, int) and isinstance(up, (int, float)) and 1 <= qty <= 99 and up > 0:
            total += qty * up

    if isinstance(amount, (int, float)) and amount != total:
        errs.append("total")
    return errs
