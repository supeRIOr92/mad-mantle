# main.py — RealClaw Intelligence Engine
# Entry point: starts scheduler + Telegram bot concurrently
# Usage: python main.py

import asyncio
import logging
import sys
import signal
from datetime import datetime, timezone

from config import TELEGRAM_BOT_TOKEN, SUBGRAPH_URL
from database import init_db
from scheduler import start_scheduler, scheduler, run_scan
from alerter import build_bot_app

# ── Logging Setup ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("realclaw.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("realclaw.main")


# ── Startup Banner ────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════╗
║ RealClaw Intelligence Engine ║
║ AI Alpha & Risk Detection — Mantle Network ║
║ v5.1 — Turing Test 2026 ║
╚══════════════════════════════════════════════════╝
"""


def print_startup_info():
    print(BANNER)
    logger.info("RealClaw starting up...")
    logger.info(f"Subgraph URL: {'✅ SET' if SUBGRAPH_URL else '❌ NOT SET — scans will fail'}")
    logger.info(f"Telegram Bot: {'✅ SET' if TELEGRAM_BOT_TOKEN else '❌ NOT SET — alerts disabled'}")
    logger.info(f"Start time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")


# ── Graceful Shutdown ─────────────────────────────────────

shutdown_event = asyncio.Event()


def handle_shutdown(sig, frame):
    logger.info(f"[main] Received signal {sig} — shutting down...")
    shutdown_event.set()


# ── Bot Runner ────────────────────────────────────────────

async def run_bot():
    """Run Telegram bot in async context alongside scheduler."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("[main] No bot token — Telegram bot disabled")
        await shutdown_event.wait()
        return

    app = build_bot_app()

    async with app:
        await app.start()
        logger.info("[main] Telegram bot started ✅")
        await app.updater.start_polling(drop_pending_updates=True)

        # Wait for shutdown signal
        await shutdown_event.wait()

        logger.info("[main] Stopping Telegram bot...")
        await app.updater.stop()
        await app.stop()


# ── Scheduler Runner ──────────────────────────────────────

async def run_scheduler():
    """Start APScheduler and run until shutdown."""
    start_scheduler()

    # Run first scan immediately on startup
    logger.info("[main] Running initial scan...")
    try:
        await run_scan()
    except Exception as e:
        logger.error(f"[main] Initial scan failed: {e}")

    # Wait for shutdown
    await shutdown_event.wait()

    logger.info("[main] Stopping scheduler...")
    scheduler.shutdown(wait=False)


# ── Main ──────────────────────────────────────────────────

async def main():
    print_startup_info()
    init_db()

    # Register shutdown handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("[main] Starting all services...")

    # Run bot + scheduler concurrently
    await asyncio.gather(
        run_bot(),
        run_scheduler(),
        return_exceptions=True,
    )

    logger.info("[main] RealClaw shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[main] KeyboardInterrupt — exiting.")
        sys.exit(0)