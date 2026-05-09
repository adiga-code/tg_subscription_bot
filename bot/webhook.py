"""aiohttp server that handles YuKassa payment webhook notifications."""
import asyncio
import json
import logging

from aiohttp import web
from aiogram import Bot
from sqlalchemy import select

from bot.database import Payment, async_session_factory
from bot.services.subscription import activate_subscription

logger = logging.getLogger(__name__)


def create_webhook_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/payment/webhook", handle_yukassa_webhook)
    return app


async def handle_yukassa_webhook(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]

    try:
        data = await request.json()
    except Exception:
        logger.warning("Invalid JSON in webhook body")
        return web.Response(status=400)

    event = data.get("event", "")
    obj = data.get("object", {})

    if event != "payment.succeeded":
        # Acknowledge other events without action
        return web.Response(status=200)

    payment_id = obj.get("id")
    metadata = obj.get("metadata", {})
    user_id = metadata.get("user_id")
    plan_key = metadata.get("plan_key")

    if not all([payment_id, user_id, plan_key]):
        logger.warning("Missing fields in webhook: payment_id=%s user_id=%s plan_key=%s", payment_id, user_id, plan_key)
        return web.Response(status=400)

    user_id = int(user_id)

    # Verify payment status independently via API to avoid spoofed webhooks
    try:
        from bot.services.yukassa import get_payment_status
        status = await asyncio.to_thread(get_payment_status, payment_id)
        if status != "succeeded":
            return web.Response(status=200)
    except Exception as e:
        logger.error("Failed to verify payment %s: %s", payment_id, e)
        return web.Response(status=200)

    # Check if already processed
    async with async_session_factory() as session:
        result = await session.execute(
            select(Payment).where(Payment.yukassa_payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()

        if payment and payment.status == "succeeded":
            return web.Response(status=200)  # Already handled

        # Get telegram_id for this user
        from bot.database import User
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

    if not user:
        logger.warning("User %d not found for webhook payment %s", user_id, payment_id)
        return web.Response(status=200)

    try:
        await activate_subscription(
            user_id=user_id,
            telegram_id=user.telegram_id,
            plan_key=plan_key,
            yukassa_payment_id=payment_id,
            bot=bot,
        )
        logger.info("Subscription activated for user %d, plan %s", user_id, plan_key)
    except Exception as e:
        logger.error("Failed to activate subscription: %s", e)

    return web.Response(status=200)
