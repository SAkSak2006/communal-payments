from decimal import Decimal
from typing import Optional


def validate_reading(
    new_value: Decimal,
    previous_value: Decimal,
) -> Optional[str]:
    """Validate meter reading. Returns error message or None if valid."""
    if new_value < 0:
        return "Показание не может быть отрицательным"

    if new_value < previous_value:
        return f"Новое показание ({new_value}) меньше предыдущего ({previous_value})"

    return None


def is_anomalous_reading(
    consumption: Decimal,
    previous_value: Decimal,
    threshold: int = 3,
) -> bool:
    """Check if consumption is anomalously high (> threshold * previous)."""
    if previous_value <= 0:
        return False
    return consumption > previous_value * threshold


def validate_personal_account(account: str) -> Optional[str]:
    """Validate personal account format."""
    if not account or len(account.strip()) < 3:
        return "Лицевой счёт должен содержать минимум 3 символа"
    return None


def validate_phone(phone: str) -> Optional[str]:
    """Basic phone validation."""
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+") and not cleaned.isdigit():
        return "Некорректный формат телефона"
    digits = cleaned.lstrip("+")
    if len(digits) < 10 or len(digits) > 15:
        return "Телефон должен содержать от 10 до 15 цифр"
    return None
