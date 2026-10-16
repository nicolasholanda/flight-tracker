import warnings
from datetime import date, datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, TypeHandler
from telegram.warnings import PTBUserWarning

from flight_tracker.bot.access import guard, on_access_decision, start
from flight_tracker.bot.admin import on_revoke, revoke_command, users_command
from flight_tracker.bot.search import alert_conversation, search_conversation
from flight_tracker.bot.watches import list_alerts, on_history, on_remove
from flight_tracker.config import Settings
from flight_tracker.db import connect, migrate
from flight_tracker.notifiers.telegram import TelegramNotifier
from flight_tracker.providers.google_flights import GoogleFlightsProvider
from flight_tracker.repositories.check_run_repository import CheckRunRepository
from flight_tracker.repositories.search_request_repository import SearchRequestRepository
from flight_tracker.repositories.snapshot_repository import SnapshotRepository
from flight_tracker.repositories.user_repository import UserRepository
from flight_tracker.repositories.watch_repository import WatchRepository
from flight_tracker.services.access_service import AccessService
from flight_tracker.services.city_resolver import CityResolver
from flight_tracker.services.price_checker import PriceChecker
from flight_tracker.services.quota_service import QuotaService
from flight_tracker.services.search_service import SearchService
from flight_tracker.services.watch_service import WatchService

warnings.filterwarnings("ignore", message=r".*per_message.*", category=PTBUserWarning)


def build_application(settings: Settings) -> Application:
    conn = connect(settings.database_path)
    migrate(conn)

    access = AccessService(UserRepository(conn), settings.owner_chat_id)
    access.ensure_owner()
    provider = GoogleFlightsProvider(settings.currency, settings.language)
    watch_repository = WatchRepository(conn)
    quota = QuotaService(
        SearchRequestRepository(conn),
        watch_repository,
        settings.max_searches_per_user_per_hour,
        settings.max_active_watches_per_user,
    )
    zone = ZoneInfo(settings.timezone)

    def today() -> date:
        return datetime.now(zone).date()

    snapshots = SnapshotRepository(conn)
    app = ApplicationBuilder().token(settings.telegram_token).build()
    price_checker = PriceChecker(
        watch_repository,
        snapshots,
        CheckRunRepository(conn),
        provider,
        TelegramNotifier(app.bot),
        settings.max_routes_per_run,
        settings.request_delay_seconds,
        today,
    )
    app.bot_data.update(
        settings=settings,
        owner_chat_id=settings.owner_chat_id,
        access=access,
        city_resolver=CityResolver.from_csv(),
        search=SearchService(provider, settings.request_delay_seconds),
        quota=quota,
        watches=WatchService(watch_repository, quota),
        price_checker=price_checker,
        snapshots=snapshots,
    )

    app.add_handler(TypeHandler(Update, guard), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_access_decision, pattern=r"^access:"))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("revoke", revoke_command))
    app.add_handler(CallbackQueryHandler(on_revoke, pattern=r"^admin:revoke:"))
    app.add_handler(search_conversation())
    app.add_handler(alert_conversation())
    app.add_handler(CommandHandler("alertas", list_alerts))
    app.add_handler(CallbackQueryHandler(list_alerts, pattern=r"^menu:alerts$"))
    app.add_handler(CallbackQueryHandler(on_remove, pattern=r"^watch:remove:"))
    app.add_handler(CallbackQueryHandler(on_history, pattern=r"^watch:history:"))

    app.job_queue.run_repeating(
        check_prices,
        interval=settings.check_interval_minutes * 60,
        first=60,
        name="price-check",
        job_kwargs={"jitter": settings.check_jitter_seconds, "max_instances": 1, "coalesce": True},
    )
    return app


async def check_prices(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot_data["price_checker"].run()
