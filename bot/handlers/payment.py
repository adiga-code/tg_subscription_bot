import asyncio

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.config import PLANS, config
from bot.database import Payment, Subscription, User, async_session_factory
from bot.keyboards import pay_button, payment_link_keyboard
from bot.services.subscription import activate_subscription
from bot.services.yukassa import create_payment, get_payment_status
from bot.states import PaymentFlow

router = Router()


async def _create_and_send_payment(
    bot: Bot,
    message: Message,
    user: User,
    plan_key: str,
) -> None:
    plan = PLANS[plan_key]
    try:
        payment_data = await asyncio.to_thread(
            create_payment,
            amount=plan["price"],
            plan_key=plan_key,
            user_id=user.id,
            email=user.email,
            return_url=f"https://t.me/{config.BOT_USERNAME}",
        )
    except Exception:
        await message.answer(
            "❌ Не удалось создать платёж. Попробуйте позже или обратитесь в поддержку.",
            reply_markup=pay_button(plan_key),
        )
        return

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

    role_label = "резидента" if user.role == "resident" else "участника"
    await message.answer(
        f"💳 <b>Оплата подписки {role_label}</b>\n\n"
        f"Сумма: <b>{plan['price']:,} ₽/мес.</b>\n\n".replace(",", " ") +
        "Нажмите кнопку ниже для перехода на страницу оплаты.\n"
        "После оплаты нажмите «Я оплатил» — мы проверим платёж и выдадим доступ.",
        reply_markup=payment_link_keyboard(payment_data["confirmation_url"], plan_key),
    )


@router.callback_query(F.data.startswith("pay:"))
async def initiate_payment(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    plan_key = callback.data.split(":")[1]
    tg_id = callback.from_user.id

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

    if not user:
        await callback.answer("Пожалуйста, введите /start для начала.", show_alert=True)
        return

    if not user.email:
        await state.update_data(pending_plan_key=plan_key)
        await state.set_state(PaymentFlow.waiting_email)
        await callback.message.answer(
            "Для оформления подписки введите ваш <b>email</b> (нужен для формирования чека):"
        )
        await callback.answer()
        return

    await callback.answer("⏳ Создаём ссылку на оплату…")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _create_and_send_payment(bot, callback.message, user, plan_key)


@router.message(PaymentFlow.waiting_email)
async def payment_email_input(message: Message, state: FSMContext, bot: Bot) -> None:
    email = message.text.strip().lower()

    if "@" not in email or "." not in email.split("@")[-1]:
        await message.answer("Пожалуйста, введите корректный email:")
        return

    data = await state.get_data()
    plan_key = data.get("pending_plan_key", "1m")
    await state.clear()

    tg_id = message.from_user.id
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.email = email
            await session.commit()

    if not user:
        await message.answer("Ошибка: пользователь не найден. Введите /start.")
        return

    await message.answer("⏳ Создаём ссылку на оплату...")
    await _create_and_send_payment(bot, message, user, plan_key)


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
            .limit(1)
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
            "❌ Платёж отменён.\n\nЕсли хотите попробовать снова — нажмите кнопку ниже.",
            reply_markup=pay_button(plan_key),
        )
    else:
        await callback.answer()
        await callback.message.answer(
            "⏳ Оплата ещё не прошла.\n\n"
            "Если вы уже оплатили — подождите немного и нажмите «✅ Я оплатил» снова."
        )


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Платёж отменён. Вы можете оформить подписку снова.",
        reply_markup=pay_button("1m"),
    )
