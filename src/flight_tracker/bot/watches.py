from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from flight_tracker.bot.formatting import format_watch, main_menu
from flight_tracker.domain import Watch
from flight_tracker.services.watch_service import WatchService


def _watches(context: ContextTypes.DEFAULT_TYPE) -> WatchService:
    return context.bot_data["watches"]


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    chat = update.effective_chat
    watches = _watches(context).list_active(update.effective_user.id)
    if not watches:
        await chat.send_message("Você não tem alertas ativos. Faça uma busca para criar um. 🔍", reply_markup=main_menu())
        return
    limit = context.bot_data["quota"].max_active_watches
    await chat.send_message(f"🔔 Seus alertas ativos ({len(watches)}/{limit}):")
    for watch in watches:
        await chat.send_message(format_watch(watch), parse_mode=ParseMode.HTML, reply_markup=watch_keyboard(watch))


def watch_keyboard(watch: Watch) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Remover", callback_data=f"watch:remove:{watch.id}")]])


async def on_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    watch_id = int(query.data.split(":")[2])
    if not _watches(context).remove(update.effective_user.id, watch_id):
        await query.answer("Esse alerta já não está ativo.")
        return
    await query.answer()
    await query.edit_message_text("🛑 Alerta removido.")
