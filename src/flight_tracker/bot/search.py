from datetime import date, datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from flight_tracker.bot.formatting import format_results, format_watch, main_menu, parse_date, parse_price
from flight_tracker.domain import TripType
from flight_tracker.providers.base import ProviderError
from flight_tracker.services.city_resolver import CityOption, CityResolver
from flight_tracker.services.watch_service import WatchLimitReached

TRIP, ORIGIN, DESTINATION, DEPARTURE, RETURN, TARGET_PRICE = range(6)


def _today(context: ContextTypes.DEFAULT_TYPE) -> date:
    return datetime.now(ZoneInfo(context.bot_data["settings"].timezone)).date()


def _draft(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault("draft", {})


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data["draft"] = {}
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("➡️ Só ida", callback_data=f"trip:{TripType.ONE_WAY}"),
            InlineKeyboardButton("↔️ Ida e volta", callback_data=f"trip:{TripType.ROUND_TRIP}"),
        ]]
    )
    await update.effective_chat.send_message("Escolha o tipo de pesquisa, por favor 👇", reply_markup=keyboard)
    return TRIP


async def on_trip_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    trip_type = TripType(query.data.split(":", 1)[1])
    _draft(context)["trip_type"] = trip_type
    label = "➡️ Só ida" if trip_type == TripType.ONE_WAY else "↔️ Ida e volta"
    await query.edit_message_text(f"Tipo de pesquisa: {label}")
    await update.effective_chat.send_message("Digite a cidade de partida (por exemplo: Rio de Janeiro).")
    return ORIGIN


async def on_origin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _resolve_city(update, context, "origin", ORIGIN)


async def on_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _resolve_city(update, context, "destination", DESTINATION)


async def on_origin_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _pick_city(update, context, "origin", ORIGIN)


async def on_destination_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _pick_city(update, context, "destination", DESTINATION)


async def _resolve_city(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, state: int) -> int:
    resolver: CityResolver = context.bot_data["city_resolver"]
    options = resolver.resolve(update.message.text)
    if not options:
        await update.message.reply_text("Não encontrei essa cidade. 😕 Tente novamente (por exemplo: Fortaleza ou FOR).")
        return state
    if len(options) == 1:
        return await _set_city(update, context, field, options[0], state)
    context.user_data["city_options"] = options
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(option.label, callback_data=f"city:{index}")] for index, option in enumerate(options)]
    )
    await update.message.reply_text(
        "Eu não estou certo quanto à cidade. Por favor, selecione a partir da lista 👇", reply_markup=keyboard
    )
    return state


async def _pick_city(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, state: int) -> int:
    query = update.callback_query
    await query.answer()
    options: list[CityOption] = context.user_data.get("city_options", [])
    index = int(query.data.split(":", 1)[1])
    if index >= len(options):
        return state
    option = options[index]
    context.user_data.pop("city_options", None)
    await query.edit_message_text(f"✔️ {option.label}")
    return await _set_city(update, context, field, option, state)


async def _set_city(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str, option: CityOption, state: int) -> int:
    draft = _draft(context)
    if field == "origin":
        draft["origin"] = option
        await update.effective_chat.send_message("Agora, digite a cidade de chegada (por exemplo: Brasília).")
        return DESTINATION
    if set(option.codes) & set(draft["origin"].codes):
        await update.effective_chat.send_message("A cidade de chegada precisa ser diferente da partida. Tente outra.")
        return state
    draft["destination"] = option
    await update.effective_chat.send_message(
        "Boa escolha! Especifique a data de ida (por exemplo: 17/10/2026)."
    )
    return DEPARTURE


async def on_departure(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    departure = await _read_date(update, context, minimum=_today(context))
    if departure is None:
        return DEPARTURE
    draft = _draft(context)
    draft["departure_date"] = departure
    if draft["trip_type"] == TripType.ROUND_TRIP:
        await update.message.reply_text("E a data de volta? (por exemplo: 24/10/2026)")
        return RETURN
    draft["return_date"] = None
    return await _run_search(update, context)


async def on_return(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = _draft(context)
    return_date = await _read_date(update, context, minimum=draft["departure_date"])
    if return_date is None:
        return RETURN
    draft["return_date"] = return_date
    return await _run_search(update, context)


async def _read_date(update: Update, context: ContextTypes.DEFAULT_TYPE, minimum: date) -> date | None:
    value = parse_date(update.message.text, _today(context))
    if value is None:
        await update.message.reply_text("Data inválida. Use o formato dd/mm/aaaa (por exemplo: 17/10/2026).")
        return None
    if value < minimum:
        await update.message.reply_text(f"A data precisa ser a partir de {minimum:%d/%m/%Y}.")
        return None
    return value


async def _run_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = context.user_data.pop("draft")
    quota = context.bot_data["quota"]
    if not quota.try_consume_search(update.effective_user.id):
        await update.message.reply_text(
            f"Você atingiu o limite de {quota.max_searches_per_hour} buscas por hora. Tente novamente mais tarde. ⏳"
        )
        return ConversationHandler.END
    await update.message.reply_text("Ok, aguarde alguns segundos 🔍")
    try:
        offers = await context.bot_data["search"].search(
            draft["origin"].codes, draft["destination"].codes, draft["departure_date"], draft["return_date"]
        )
    except ProviderError:
        await update.message.reply_text("Não consegui buscar os preços agora. 😕 Tente novamente em alguns minutos.")
        return ConversationHandler.END
    context.user_data["last_search"] = draft
    text = format_results(
        draft["origin"].display, draft["destination"].display, draft["departure_date"], draft["return_date"], offers
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=_results_keyboard(),
    )
    return ConversationHandler.END


def _results_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔔 Criar alerta de preço", callback_data="alert:create")]]
        + list(main_menu().inline_keyboard)
    )


async def start_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    if "last_search" not in context.user_data:
        await update.effective_chat.send_message("Faça uma busca primeiro. 🔍", reply_markup=main_menu())
        return ConversationHandler.END
    quota = context.bot_data["quota"]
    if not quota.can_create_watch(update.effective_user.id):
        await update.effective_chat.send_message(_limit_text(quota.max_active_watches))
        return ConversationHandler.END
    await update.effective_chat.send_message(
        "Qual o preço máximo que você quer pagar? (por exemplo: 1500)\n"
        "Te aviso quando aparecer um voo por esse valor ou menos. 🔔"
    )
    return TARGET_PRICE


async def on_target_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_price = parse_price(update.message.text)
    if target_price is None:
        await update.message.reply_text("Valor inválido. Digite só o número (por exemplo: 1500 ou 1.499,90).")
        return TARGET_PRICE
    search = context.user_data["last_search"]
    try:
        watch = context.bot_data["watches"].create(
            update.effective_user.id,
            search["trip_type"],
            search["origin"],
            search["destination"],
            search["departure_date"],
            search["return_date"],
            target_price,
        )
    except WatchLimitReached:
        await update.message.reply_text(_limit_text(context.bot_data["quota"].max_active_watches))
        return ConversationHandler.END
    await update.message.reply_text(
        f"🔔 Alerta criado!\n\n{format_watch(watch)}\n\n"
        "Vou verificar os preços a cada hora e te aviso quando bater o valor. ✈️",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


def _limit_text(limit: int) -> str:
    return f"Você atingiu o limite de {limit} alertas ativos. Remova algum para criar outro."


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("draft", None)
    context.user_data.pop("city_options", None)
    await update.message.reply_text("Cancelado.", reply_markup=main_menu())
    return ConversationHandler.END


def search_conversation() -> ConversationHandler:
    text = filters.TEXT & ~filters.COMMAND
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_search, pattern=r"^menu:search$"),
            CommandHandler("buscar", start_search),
        ],
        states={
            TRIP: [CallbackQueryHandler(on_trip_type, pattern=r"^trip:")],
            ORIGIN: [MessageHandler(text, on_origin), CallbackQueryHandler(on_origin_pick, pattern=r"^city:")],
            DESTINATION: [
                MessageHandler(text, on_destination),
                CallbackQueryHandler(on_destination_pick, pattern=r"^city:"),
            ],
            DEPARTURE: [MessageHandler(text, on_departure)],
            RETURN: [MessageHandler(text, on_return)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
        allow_reentry=True,
        conversation_timeout=900,
    )


def alert_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_alert, pattern=r"^alert:create$")],
        states={TARGET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_target_price)]},
        fallbacks=[CommandHandler("cancelar", cancel)],
        allow_reentry=True,
        conversation_timeout=900,
    )
