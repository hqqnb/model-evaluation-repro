"""MA 参考测试集（覆盖全部植入缺陷的合法写法）。"""

import importlib.util
import os
import pathlib


def _load():
    target = os.environ["TARGET_IMPL"]
    spec = importlib.util.spec_from_file_location("target_impl", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = _load().validate_order


def base(items=None, amount=None, currency="USD", email="a@b.com", oid="o1"):
    return {
        "id": oid,
        "amount": 10.0 if amount is None else amount,
        "currency": currency,
        "email": email,
        "items": [{"name": "x", "qty": 1, "unit_price": 10}] if items is None else items,
    }


def test_valid_order_empty_errors():
    assert V(base()) == []


def test_amount_zero_rejected():
    assert "amount" in V(base(amount=0))


def test_amount_negative_rejected():
    assert "amount" in V(base(amount=-1))


def test_amount_too_large_rejected():
    assert "amount" in V(base(amount=10001))


def test_currency_lowercase_rejected():
    assert V(base(currency="usd")) != []


def test_currency_bad_length_rejected():
    assert V(base(currency="US")) != []


def test_currency_digits_rejected():
    assert V(base(currency="U1D")) != []


def test_email_no_at_rejected():
    assert V(base(email="nope")) != []


def test_email_no_domain_dot_rejected():
    assert V(base(email="a@b")) != []


def test_email_valid_accepted():
    assert V(base(email="a.b+c@example.co")) == []


def test_empty_id_rejected():
    assert V(base(oid="")) != []


def test_empty_items_rejected():
    assert V(base(items=[])) != []


def test_too_many_items_rejected():
    assert V(base(items=[{"name": "x", "qty": 1, "unit_price": 1}] * 51)) != []


def test_qty_zero_rejected():
    assert V(base(items=[{"name": "x", "qty": 0, "unit_price": 1}])) != []


def test_qty_noninteger_rejected():
    assert V(base(items=[{"name": "x", "qty": 1.5, "unit_price": 1}])) != []


def test_unit_price_zero_rejected():
    assert V(base(items=[{"name": "x", "qty": 1, "unit_price": 0}])) != []


def test_name_empty_rejected():
    assert V(base(items=[{"name": "", "qty": 1, "unit_price": 1}])) != []


def test_total_mismatch_rejected():
    assert V(base(items=[{"name": "x", "qty": 2, "unit_price": 3}], amount=5)) != []


def test_float_rounding_tolerance_accepted():
    # 0.1 + 0.2 != 0.3 精确比较会误报
    items = [
        {"name": "a", "qty": 1, "unit_price": 0.1},
        {"name": "b", "qty": 1, "unit_price": 0.2},
    ]
    assert V(base(items=items, amount=0.3)) == []


def test_multiple_errors_reported():
    assert len(V(base(amount=0, currency="x", email="bad"))) >= 3
