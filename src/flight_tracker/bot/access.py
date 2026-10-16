from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationHandlerStop, ContextTypes

from flight_tracker.services.access_service import AccessService


def _access(context: ContextTypes.DEFAULT_TYPE) -> AccessService:
    return context.bot_data["access"]


async def guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        raise ApplicationHandlerStop
    access = _access(context)
    if access.is_allowed(user.id):
        return
    if update.message is not None:
        created = access.request_access(user.id, user.full_name, user.username)
        if created is not None:
            await update.message.reply_text(
                "🔒 Acesso restrito. Seu pedido foi enviado ao administrador."
            )
            await _notify_owner(context, user.id, user.full_name, user.username)
    raise ApplicationHandlerStop


async def _notify_owner(context: ContextTypes.DEFAULT_TYPE, chat_id: int, name: str, username: str | None) -> None:
    handle = f" (@{escape(username)})" if username else ""
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Aprovar", callback_data=f"access:approve:{chat_id}"),
            InlineKeyboardButton("❌ Negar", callback_data=f"access:deny:{chat_id}"),
        ]]
    )
    await context.bot.send_message(
        context.bot_data["owner_chat_id"],
        f"🙋 Novo pedido de acesso\n<b>{escape(name)}</b>{handle}\nID: <code>{chat_id}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def on_access_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    access = _access(context)
    if not access.is_owner(update.effective_user.id):
        await query.answer()
        return
    _, action, raw_id = query.data.split(":")
    chat_id = int(raw_id)
    user = access.approve(chat_id) if action == "approve" else access.deny(chat_id)
    if user is None:
        await query.answer("Nada a fazer para este usuário.")
        return
    await query.answer()
    label = "✅ Aprovado" if action == "approve" else "❌ Negado"
    await query.edit_message_text(f"{label}: <b>{escape(user.name)}</b> (<code>{chat_id}</code>)", parse_mode=ParseMode.HTML)
    if action == "approve":
        await context.bot.send_message(chat_id, "🎉 Seu acesso foi aprovado! Envie /start para começar.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Olá, {update.effective_user.first_name}! 👋 Bem-vindo ao Flight Tracker."
    )
