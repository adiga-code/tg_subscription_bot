from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.keyboards import faq_back_keyboard, support_keyboard

router = Router()

FAQ_TEXT = (
    "❓ <b>Часто задаваемые вопросы</b>\n\n"
    "<b>Как получить доступ после оплаты?</b>\n"
    "Доступ выдаётся автоматически — бот отправит ссылку на канал сразу после подтверждения оплаты.\n\n"
    "<b>Что если ссылка не пришла?</b>\n"
    "Нажмите «Я оплатил» в сообщении с оплатой или обратитесь к менеджеру.\n\n"
    "<b>Можно ли продлить подписку?</b>\n"
    "Да. Зайдите в раздел «Тарифы» и оформите новую подписку — она прибавится к текущей.\n\n"
    "<b>Как отменить подписку?</b>\n"
    "Подписка не продлевается автоматически. По истечении срока доступ закрывается.\n\n"
    "<b>Какие способы оплаты доступны?</b>\n"
    "Оплата картой и через СБП — через платёжную систему ЮKassa.\n\n"
    "<b>Есть другие вопросы?</b>\n"
    "Обратитесь к нашему менеджеру — ответим быстро!"
)


@router.message(F.text == "💬 Поддержка")
async def show_support(message: Message) -> None:
    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Если у вас есть вопросы — напишите нашему менеджеру или ознакомьтесь с FAQ.",
        reply_markup=support_keyboard(config.SUPPORT_USERNAME),
    )


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery) -> None:
    await callback.message.edit_text(FAQ_TEXT, reply_markup=faq_back_keyboard())


@router.callback_query(F.data == "back:support")
async def back_to_support(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "💬 <b>Поддержка</b>\n\n"
        "Если у вас есть вопросы — напишите нашему менеджеру или ознакомьтесь с FAQ.",
        reply_markup=support_keyboard(config.SUPPORT_USERNAME),
    )
