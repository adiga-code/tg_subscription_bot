import asyncio

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from bot.config import PLANS, config
from bot.database import Payment, Subscription, User, async_session_factory
from bot.keyboards import payment_link_keyboard, plans_keyboard
from bot.services.yukassa import create_payment, get_payment_status
from bot.services.subscription import activate_subscription

router = Router()


@router.callback_query(F.data.startswith("pay:"))
async def initiate_payment(callback: CallbackQuery, bot: Bot) -> None:
    plan_key = callback.data.split(":")[1]
    plan = PLANS[plan_key]
    tg_id = callback.from_user.id

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

        if not user or not user.email:
            await callback.answer("Введите /start и укажите email", show_alert=True)
            return

        # Check for existing active subscription
        sub_result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
            )
        )
        active_sub = sub_result.scalar_one_or_none()

    await callback.message.edit_text("⏳ Создаём ссылку на оплату...")

    try:
        payment_data = await asyncio.to_thread(
            create_payment,
            amount=plan["price"],
            plan_key=plan_key,
            user_id=user.id,
            email=user.email,
            return_url=f"https://t.me/{config.BOT_USERNAME}",
        )
    except Exception as e:
        await callback.message.edit_text(
            "❌ Не удалось создать платёж. Попробуйте позже или обратитесь в поддержку.",
            reply_markup=plans_keyboard(),
        )
        return

    # Save pending payment to DB
    async with async_session_factory() as session:
        payment = Payment(
            user_id=user.id,
            yukassa_payment_id=payment_data["id"],
            plan_key=plan_key,
            amount=plan["price"],
            status="pending",
        )
        session.add(payment)
        await session.commit()

    await callback.message.edit_text(
        f"💳 <b>Оплата тарифа «{plan['name']}»</b>\n\n"
        f"Сумма: <b>{plan['price']:,} ₽</b>\n\n".replace(",", " ") +
        "Нажмите кнопку ниже для перехода на страницу оплаты.\n"
        "После оплаты нажмите «Я оплатил» — мы проверим платёж и выдадим доступ.",
        reply_markup=payment_link_keyboard(payment_data["confirmation_url"], plan_key),
    )


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery, bot: Bot) -> None:
    plan_key = callback.data.split(":")[1]
    tg_id = callback.from_user.id

    await callback.answer("Проверяем платёж...", show_alert=False)

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        payment_result = await session.execute(
            select(Payment)
            .where(Payment.user_id == user.id, Payment.plan_key == plan_key, Payment.status == "pending")
            .order_by(Payment.created_at.desc())
        )
        payment = payment_result.scalar_one_or_none()

    if not payment or not payment.yukassa_payment_id:
        await callback.message.edit_text("Платёж не найден. Попробуйте начать оформление заново.")
        return

    try:
        status = await asyncio.to_thread(get_payment_status, payment.yukassa_payment_id)
    except Exception:
        await callback.answer("Ошибка при проверке платежа. Попробуйте чуть позже.", show_alert=True)
        return

    if status == "succeeded":
        await activate_subscription(
            user_id=user.id,
            telegram_id=tg_id,
            plan_key=plan_key,
            yukassa_payment_id=payment.yukassa_payment_id,
            bot=bot,
        )
        await callback.message.edit_text(
            "✅ <b>Оплата прошла успешно!</b>\n\n"
            "Добро пожаловать в закрытое сообщество! 🎉\n"
            "Ссылка на канал отправлена выше."
        )
    elif status == "canceled":
        async with async_session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.yukassa_payment_id == payment.yukassa_payment_id)
            )
            p = result.scalar_one_or_none()
            if p:
                p.status = "canceled"
                await session.commit()
        await callback.message.edit_text(
            "❌ Платёж отменён.\n\nЕсли хотите попробовать снова — выберите тариф.",
            reply_markup=plans_keyboard(),
        )
    else:
        await callback.answer(
            "Платёж ещё не завершён. Если вы уже оплатили — подождите минуту и нажмите снова.",
            show_alert=True,
        )


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Платёж отменён. Вы можете выбрать тариф снова.",
        reply_markup=plans_keyboard(),
    )
