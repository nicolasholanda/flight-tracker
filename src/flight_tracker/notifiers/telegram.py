from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.constants import ParseMode

from flight_tracker.bot.formatting import format_alert
from flight_tracker.domain import FlightOffer, Watch


class TelegramNotifier:
    def __init__(self, bot: Bot, owner_chat_id: int):
        self._bot = bot
        self._owner_chat_id = owner_chat_id

    async def send_owner_message(self, text: str) -> None:
        await self._bot.send_message(self._owner_chat_id, text)

    async def send_price_alert(self, watch: Watch, offer: FlightOffer) -> None:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🛒 Ver no Google Flights", url=offer.booking_url)],
                [
                    InlineKeyboardButton("📈 Histórico", callback_data=f"watch:history:{watch.id}"),
                    InlineKeyboardButton("🛑 Parar alerta", callback_data=f"watch:remove:{watch.id}"),
                ],
            ]
        )
        await self._bot.send_message(
            watch.chat_id,
            format_alert(watch, offer),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
            reply_markup=keyboard,
        )
