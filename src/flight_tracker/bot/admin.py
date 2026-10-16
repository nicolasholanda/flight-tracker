from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from flight_tracker.domain import AppUser, UserStatus
from flight_tracker.services.access_service import AccessService

STATUS_LABELS = {
    UserStatus.PENDING: "⏳ pendente",
    UserStatus.APPROVED: "✅ aprovado",
    UserStatus.DENIED: "❌ negado",
    UserStatus.REVOKED: "🚫 revogado",
}


def _access(context: ContextTypes.DEFAULT_TYPE) -> AccessService:
    return context.bot_data["access"]


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    access = _access(context)
    if not access.is_owner(update.effective_user.id):
        return
    users = access.list_users()
    if not users:
        await update.message.reply_text("Nenhum usuário além de você.")
        return
    lines = ["👥 <b>Usuários</b>", ""] + [_describe(user) for user in users]
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[_action_button(user)] for user in users]),
    )


async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    access = _access(context)
    if not access.is_owner(update.effective_user.id):
        return
    if len(context.args) != 1 or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Uso: /revoke <id>")
        return
    user = access.revoke(int(context.args[0]))
    if user is None:
        await update.message.reply_text("Usuário não encontrado ou não está aprovado.")
        return
    await update.message.reply_text(f"🚫 Acesso revogado: {user.name}")


async def on_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    access = _access(context)
    if not access.is_owner(update.effective_user.id):
        await query.answer()
        return
    user = access.revoke(int(query.data.split(":")[2]))
    if user is None:
        await query.answer("Nada a fazer para este usuário.")
        return
    await query.answer()
    await query.edit_message_text(
        f"🚫 Acesso revogado: <b>{escape(user.name)}</b> (<code>{user.chat_id}</code>)",
        parse_mode=ParseMode.HTML,
    )


def _describe(user: AppUser) -> str:
    handle = f" @{escape(user.username)}" if user.username else ""
    return f"• <b>{escape(user.name)}</b>{handle} — <code>{user.chat_id}</code> — {STATUS_LABELS[user.status]}"


def _action_button(user: AppUser) -> InlineKeyboardButton:
    if user.status == UserStatus.APPROVED:
        return InlineKeyboardButton(f"🚫 Revogar {user.name}", callback_data=f"admin:revoke:{user.chat_id}")
    return InlineKeyboardButton(f"✅ Aprovar {user.name}", callback_data=f"access:approve:{user.chat_id}")
