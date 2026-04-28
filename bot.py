"""
bot.py
MAD — Mantle Anomaly Detector
Interactive Telegram bot commands via polling.
Commands: /start, /score, /wallet, /digest, /help
"""

import logging
import asyncio
from datetime import datetime, timezone
import httpx
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ── HTTP helpers ──────────────────────────────────────────

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        })

async def get_updates(offset: int = 0) -> list:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{TELEGRAM_API}/getUpdates", params={
            "offset": offset,
            "timeout": 25,
            "allowed_updates": ["message"],
        })
        data = resp.json()
        return data.get("result", [])

# ── Command handlers ──────────────────────────────────────

async def cmd_start(chat_id: int):
    text = (
        "🚨 MAD — Mantle Anomaly Detector\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Commands:\n"
        "/score — Latest anomaly scores\n"
        "/wallet <address> — Wallet profile\n"
        "/digest — Today's summary\n"
        "/help — Show this menu\n\n"
        "Dashboard: https://madmantle.vercel.app"
    )
    await send_message(chat_id, text)

async def cmd_help(chat_id: int):
    await cmd_start(chat_id)

async def cmd_score(chat_id: int):
    try:
        from database import get_recent_signals
        signals = get_recent_signals(limit=5)
        if not signals:
            await send_message(chat_id, "No signals yet — scanner is warming up.")
            return

        lines = ["📊 Latest Anomaly Scores", "━" * 35, ""]
        for s in signals:
            level = s.get("alert_level", "none").upper()
            score = s.get("s_final", 0)
            dex   = s.get("dex", "").upper()
            pool  = s.get("pool_address", "")[:8] + ".."
            ts    = s.get("created_at", "")[:16]
            emoji = "🔴" if level in ("ALERT","HIGH_CONF") else "🟡" if level == "WATCHING" else "🟢"
            lines.append(f"{emoji} {score:.0f}/100 — {dex} {pool}")
            lines.append(f"   {level} · {ts} UTC")
            lines.append("")

        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"Error fetching scores: {e}")

async def cmd_wallet(chat_id: int, address: str):
    if not address or not address.startswith("0x"):
        await send_message(chat_id, "Usage: /wallet 0x...")
        return
    try:
        from database import get_wallet
        w = get_wallet(address)
        if not w:
            await send_message(chat_id, f"Wallet {address[:8]}.. not found in database.")
            return

        roi   = w.get("roi_7d")
        score = w.get("smart_score")
        lines = [
            f"🤖 Wallet Report",
            "━" * 35,
            f"Address    {address[:8]}..{address[-4:]}",
            f"Type       {w.get('agent_type', 'UNKNOWN')}",
            f"Archetype  {w.get('archetype', 'UNKNOWN')}",
            f"Wash       {w.get('wash_ratio', 0):.1f}× — {w.get('wash_label', '—')}",
            f"ROI 7d     {'+' if roi and roi >= 0 else ''}{roi:.1f}%" if roi else "ROI 7d     —",
            f"Score      {score:.3f}" if score else "Score      —",
            f"Rep        {w.get('reputation_score', '—')}/100",
            f"Vol        ${(w.get('total_volume_usd', 0) or 0) / 1000:.1f}K",
        ]
        await send_message(chat_id, "\n".join(lines))
    except Exception as e:await send_message(chat_id, f"Error: {e}")

async def cmd_digest(chat_id: int):
    try:
        from database import get_digest_stats
        stats = get_digest_stats()
        lines = [
            "📋 Daily Digest — MAD",
            "━" * 35,
            f"Scans      {stats.get('scan_count', 0)}",
            f"Alerts     {stats.get('alert_count', 0)}",
            f"Watching   {stats.get('watching_count', 0)}",
            f"Volume     ${stats.get('total_volume_usd', 0):,.0f}",
            "",
            f"Dashboard: https://madmantle.vercel.app",
        ]
        await send_message(chat_id, "\n".join(lines))
    except Exception as e:
        await send_message(chat_id, f"Error: {e}")

# ── Dispatcher ────────────────────────────────────────────

async def handle_message(message: dict):
    chat_id = message.get("chat", {}).get("id")
    text    = message.get("text", "").strip()

    if not chat_id or not text:
        return

    if text.startswith("/start"):
        await cmd_start(chat_id)
    elif text.startswith("/help"):
        await cmd_help(chat_id)
    elif text.startswith("/score"):
        await cmd_score(chat_id)
    elif text.startswith("/digest"):
        await cmd_digest(chat_id)
    elif text.startswith("/wallet"):
        parts = text.split()
        address = parts[1] if len(parts) > 1 else ""
        await cmd_wallet(chat_id, address)
    else:
        await send_message(chat_id, "Unknown command. Use /help")

# ── Polling loop ──────────────────────────────────────────

async def run_bot():
    logger.info("[bot] MAD Telegram bot started — polling...")
    offset = 0
    while True:
        try:
            updates = await get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")
                if message:
                    await handle_message(message)
        except Exception as e:
            logger.error("[bot] polling error: %s", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())