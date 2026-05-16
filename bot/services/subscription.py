import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import select

from bot.config import PLANS, config
from bot.database import Payment, Subscription, async_session_factory

logger = logging.getLogger(__name__)


async def activate_subscription(
    user_id: int,
    telegram_id: int,
    plan_key: str,
    yukassa_payment_id: Optional[str],
    bot: Bot,
    manual: bool = False,
) -> None:
    plan = PLANS[plan_key]
    now = datetime.utcnow()

    async with async_session_factory() as session:
        # Check if there's already an active subscription to extend
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.is_active == True)
            .order_by(Subscription.expires_at.desc())
        )
        existing = result.scalar_one_or_none()

        if existing and existing.expires_at > now:
            # Extend from current expiry
            base = existing.expires_at
        else:
            base = now

        expires_at = base + timedelta(days=30 * plan["months"])

        # Deactivate old subscription
        if existing:
            existing.is_active = False

        # Create new subscription
        sub = Subscription(
            user_id=user_id,
            plan_key=plan_key,
            started_at=now,
            expires_at=expires_at,
            is_active=True,
        )
        session.add(sub)

        # Update payment status if not manual
        if yukassa_payment_id:
            pay_result = await session.execute(
                select(Payment).where(Payment.yukassa_payment_id == yukassa_payment_id)
            )
            payment = pay_result.scalar_one_or_none()
            if payment:
                payment.status = "succeeded"

        await session.commit()

    # Grant channel access via invite link
    expires_str = expires_at.strftime("%d.%m.%Y")
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=str(config.CHANNEL_ID),
            member_limit=1,
            name=f"sub_{user_id}",
            expire_date=expires_at,
        )
        source = "вручную администратором" if manual else f"за тариф «{plan['name']}»"
        await bot.send_photo(
            chat_id=telegram_id,
            photo=FSInputFile("files/after_buying.jpg"),
            caption=f"✅ <b>Оплата прошла успешно! Добро пожаловать в клуб!</b>\n\n<i>Что дальше:</i>\nДобавься в наш закрытый чат по ссылке: {invite.invite_link}\n\nСкачай стартовый пакет материалов👇🏻 \n\nНачинай знакомиться, а бот расскажет о ближайших активностях!",
        )
        # Send additional materials
        await bot.send_photo(chat_id=telegram_id, photo=FSInputFile("files/IMG_2339.JPG"), caption="ТРЕКЕР ПОЛЕЗНЫХ ПРИВЫЧЕК:")
        await bot.send_document(chat_id=telegram_id, document=FSInputFile("files/Balans_raboty_i_zhizni_dlya_frilansera_chek_list_kotoryj_izmenit.zip"), caption="чек‑лист «Баланс работы и жизни для фрилансера»")
        await bot.send_document(chat_id=telegram_id, document=FSInputFile("files/Kak-poluchit-maksimum-ot-kluba-osoznannogo-razvitiya.zip"), caption="гайд «Как получить максимум от клуба»")
    except Exception as e:
        logger.error("Failed to create invite link for user %d, channel %s: %s", user_id, config.CHANNEL_ID, e)
        await bot.send_message(
            telegram_id,
            f"✅ <b>Подписка активирована</b> до {expires_str}.\n\n"
            "Не удалось автоматически создать ссылку на канал — обратитесь в поддержку.",
        )


async def revoke_subscription(user_id: int, telegram_id: int, bot: Bot) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.is_active == True)
        )
        subscriptions = result.scalars().all()
        for sub in subscriptions:
            sub.is_active = False
        await session.commit()

    # Remove from channel
    try:
        await bot.ban_chat_member(config.CHANNEL_ID, telegram_id)
        await bot.unban_chat_member(config.CHANNEL_ID, telegram_id)
    except Exception:
        pass

    try:
        await bot.send_message(
            telegram_id,
            "ℹ️ Ваша подписка была отозвана администратором. "
            "Если это ошибка — обратитесь в поддержку.",
        )
    except Exception:
        pass
