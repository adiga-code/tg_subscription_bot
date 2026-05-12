import uuid
from typing import Any, Dict

import yookassa
from yookassa import Payment

from bot.config import config

yookassa.Configuration.account_id = config.YUKASSA_SHOP_ID
yookassa.Configuration.secret_key = config.YUKASSA_SECRET_KEY


def create_payment(
    amount: int,
    plan_key: str,
    user_id: int,
    email: str,
    return_url: str,
) -> Dict[str, Any]:
    """Create a YuKassa payment. Returns dict with 'id' and 'confirmation_url'."""
    idempotency_key = str(uuid.uuid4())
    amount = 10
    payment = Payment.create(
        {
            "amount": {"value": f"{amount}.00", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": f"Подписка {plan_key} — пользователь {user_id}",
            "receipt": {
                "customer": {"email": email},
                "items": [
                    {
                        "description": f"Подписка {plan_key}",
                        "quantity": "1.00",
                        "amount": {"value": f"{amount}.00", "currency": "RUB"},
                        "vat_code": 1,
                        "payment_mode": "full_payment",
                        "payment_subject": "service",
                    }
                ],
            },
            "metadata": {"user_id": str(user_id), "plan_key": plan_key},
        },
        idempotency_key,
    )

    return {
        "id": payment.id,
        "confirmation_url": payment.confirmation.confirmation_url,
        "status": payment.status,
    }


def get_payment_status(yukassa_payment_id: str) -> str:
    """Fetch payment status from YuKassa: 'pending', 'succeeded', 'canceled', etc."""
    payment = Payment.find_one(yukassa_payment_id)
    return payment.status
