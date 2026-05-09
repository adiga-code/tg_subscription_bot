from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import PLANS
from bot.keyboards import pay_button, plans_keyboard

router = Router()

PLANS_TEXT = (
    "📋 <b>Тарифные планы</b>\n\n"
    "Выберите подходящий тариф для получения доступа к закрытому сообществу:\n\n"
    "🟢 <b>1 месяц</b> — 2 499 ₽\n"
    "🔵 <b>3 месяца</b> — 6 499 ₽  <i>(Экономия 13%)</i>\n"
    "🟣 <b>6 месяцев</b> — 11 999 ₽  <i>(Экономия 20%)</i>\n"
    "🟡 <b>1 год</b> — 21 999 ₽  <i>(Экономия 27%)</i>\n\n"
    "👇 Нажмите на нужный тариф:"
)


@router.message(F.text == "📋 Тарифы")
async def show_plans(message: Message) -> None:
    await message.answer(PLANS_TEXT, reply_markup=plans_keyboard())


@router.callback_query(F.data == "back:plans")
async def back_to_plans(callback: CallbackQuery) -> None:
    await callback.message.edit_text(PLANS_TEXT, reply_markup=plans_keyboard())


@router.callback_query(F.data.startswith("plan:"))
async def select_plan(callback: CallbackQuery) -> None:
    plan_key = callback.data.split(":")[1]
    plan = PLANS[plan_key]

    save_line = f"\n💰 {plan['save']}" if plan["save"] else ""
    text = (
        f"📋 <b>Тариф: {plan['name']}</b>\n\n"
        f"Стоимость: <b>{plan['price']:,} ₽</b>{save_line}\n\n".replace(",", " ") +
        "Нажмите «Оплатить», чтобы продолжить.\n"
        "После оплаты вы автоматически получите доступ к закрытому каналу."
    )
    await callback.message.edit_text(text, reply_markup=pay_button(plan_key))
