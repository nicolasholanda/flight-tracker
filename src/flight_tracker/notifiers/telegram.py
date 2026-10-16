from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.constants import ParseMode

from flight_tracker.bot.formatting import format_alert
from flight_tracker.domain import FlightOffer, Watch


class TelegramNotifier:
    def __init__(self, bot: Bot):
        self._bot = bot

    async def send_price_alert(self, watch: Watch, offer: FlightOffer) -> None:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🛒 Ver no Google Flights", url=offer.booking_url)],
                [InlineKeyboardButton("🛑 Parar alerta", callback_data=f"watch:remove:{watch.id}")],
            ]
        )
        await self._bot.send_message(
            watch.chat_id,
            format_alert(watch, offer),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
            reply_markup=keyboard,
        )
