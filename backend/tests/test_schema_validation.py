from decimal import Decimal

from app.schemas import BillIn


def test_blank_split_allocations_are_normalized_before_decimal_validation():
    bill = BillIn(
        category="飲食",
        description="固定分帳",
        amount=Decimal("750.00"),
        participant_ids=["owner"],
        split_method="FIXED",
        allocations={"owner": ""},
    )

    assert bill.allocations == {"owner": None}


def test_decimal_split_allocations_remain_exact_decimals():
    bill = BillIn(
        category="飲食",
        description="百分比分帳",
        amount=Decimal("10.01"),
        participant_ids=["a", "b"],
        split_method="PERCENTAGE",
        allocations={"a": "33.33", "b": "66.67"},
    )

    assert bill.allocations == {"a": Decimal("33.33"), "b": Decimal("66.67")}
