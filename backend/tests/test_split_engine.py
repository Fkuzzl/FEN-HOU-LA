from decimal import Decimal
import pytest

from app.split_engine import calculate_split, equal_split


def test_equal_split_exact():
    assert equal_split(Decimal("180.00"), ["b", "a", "c"]) == {"a": Decimal("60"), "b": Decimal("60"), "c": Decimal("60")}


def test_equal_split_distributes_cents_deterministically():
    assert equal_split(Decimal("10.00"), ["b", "a", "c"]) == {"a": Decimal("3.34"), "b": Decimal("3.33"), "c": Decimal("3.33")}


def test_equal_split_requires_participant():
    with pytest.raises(ValueError):
        equal_split(Decimal("1"), [])


def test_percentage_split():
    assert calculate_split(Decimal("180.00"), ["a", "b", "c"], "PERCENTAGE", {"a": Decimal("50"), "b": Decimal("30"), "c": Decimal("20")}) == {"a": Decimal("90"), "b": Decimal("54"), "c": Decimal("36")}


def test_fixed_split_with_remaining():
    assert calculate_split(Decimal("180.00"), ["a", "b", "c"], "FIXED", {"a": Decimal("30"), "b": Decimal("40"), "c": None}) == {"a": Decimal("30"), "b": Decimal("40"), "c": Decimal("110")}


def test_invalid_percentage_is_rejected():
    with pytest.raises(ValueError):
        calculate_split(Decimal("180"), ["a", "b"], "PERCENTAGE", {"a": Decimal("50"), "b": Decimal("60")})
