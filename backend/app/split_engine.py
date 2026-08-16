from decimal import Decimal, ROUND_DOWN
import json


def equal_split(amount: Decimal, participant_ids: list[str]) -> dict[str, Decimal]:
    if not participant_ids:
        raise ValueError("至少需要一位參與者")
    cents = int((amount * 100).to_integral_value())
    base, remainder = divmod(cents, len(participant_ids))
    return {user_id: Decimal(base + (1 if index < remainder else 0)) / 100 for index, user_id in enumerate(sorted(participant_ids))}


def _allocate_cents(amount: Decimal, participant_ids: list[str], weights: dict[str, Decimal], divisor: Decimal) -> dict[str, Decimal]:
    total_cents = int((amount * 100).to_integral_value())
    exact = {key: Decimal(total_cents) * weights[key] / divisor for key in participant_ids}
    floors = {key: int(exact[key].to_integral_value(rounding=ROUND_DOWN)) for key in participant_ids}
    remainder = total_cents - sum(floors.values())
    order = sorted(participant_ids, key=lambda key: (exact[key] - floors[key], key), reverse=True)
    for key in order[:remainder]:
        floors[key] += 1
    return {key: Decimal(value) / 100 for key, value in floors.items()}


def calculate_split(amount: Decimal, participant_ids: list[str], method: str = "EQUAL", allocations: dict[str, Decimal | None] | None = None) -> dict[str, Decimal]:
    if method == "EQUAL":
        return equal_split(amount, participant_ids)
    if not allocations or set(allocations) != set(participant_ids):
        raise ValueError("每位參與者都需要分帳設定")
    if method == "PERCENTAGE":
        percentages = {key: value for key, value in allocations.items() if value is not None}
        if len(percentages) != len(participant_ids) or sum(percentages.values()) != Decimal("100"):
            raise ValueError("百分比總和必須是 100%")
        if any(value < 0 for value in percentages.values()):
            raise ValueError("百分比不可為負數")
        return _allocate_cents(amount, participant_ids, percentages, Decimal("100"))
    if method == "FIXED":
        remaining = [key for key, value in allocations.items() if value is None]
        fixed = {key: value for key, value in allocations.items() if value is not None}
        if len(remaining) != 1 or any(value < 0 for value in fixed.values()) or sum(fixed.values()) > amount:
            raise ValueError("固定金額必須不超過總額，並只保留一位剩餘")
        return {**fixed, remaining[0]: amount - sum(fixed.values())}
    raise ValueError("不支援的分帳方式")


def parse_allocations(value: str | None) -> dict[str, Decimal | None] | None:
    if not value:
        return None
    raw = json.loads(value)
    return {key: (Decimal(item) if item is not None else None) for key, item in raw.items()}
