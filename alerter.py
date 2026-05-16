"""
alerter.py
Telegram alert delivery for MAD — Mantle Anomaly Detector.
Three alert types: ANOMALY, SMART_MONEY, DAILY_DIGEST.
"""

import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
import httpx
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    DEMO_MODE,
    TELEGRAM_DEMO_CHANNEL_ID,
    THRESHOLD_ALERT,
    THRESHOLD_HIGH_CONF,
    THRESHOLD_WATCHING,
)

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
MANTLESCAN_TX = "https://mantlescan.xyz/tx/{hash}"

# ── Rate limiting ─────────────────────────────────────────────────────────────

_last_sent_ts: float = 0.0
_RATE_LIMIT_SEC = 3.0


async def _rate_limited_send(payload: dict) -> bool:
    global _last_sent_ts

    channel_id = (
        TELEGRAM_DEMO_CHANNEL_ID
        if DEMO_MODE and TELEGRAM_DEMO_CHANNEL_ID
        else TELEGRAM_CHANNEL_ID
    )

    if not TELEGRAM_BOT_TOKEN or not channel_id:
        logger.warning("[alerter] TELEGRAM_BOT_TOKEN or channel_id not set — skip")
        return False

    payload = {**payload, "chat_id": channel_id, "parse_mode": "HTML"}

    elapsed = time.time() - _last_sent_ts
    if elapsed < _RATE_LIMIT_SEC:
        await asyncio.sleep(_RATE_LIMIT_SEC - elapsed)

    url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage")

    for attempt in range(1, 4):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                _last_sent_ts = time.time()
                logger.info("[alerter] Message sent — attempt %d", attempt)
                return True
        except httpx.HTTPStatusError as e:
            logger.warning("[alerter] HTTP %s on attempt %d: %s", e.response.status_code, attempt, e)
            if attempt < 3:
                await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.warning("[alerter] Send error attempt %d: %s", attempt, e)
            if attempt < 3:
                await asyncio.sleep(2 ** attempt)

    logger.error("[alerter] All 3 send attempts failed")
    return False


# ── Score helpers ─────────────────────────────────────────────────────────────

def _score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 100) * width)
    return "█" * filled + "░" * (width - filled)


def _score_label(score: float) -> str:
    if score >= THRESHOLD_HIGH_CONF:
        return "HIGH CONFIDENCE"
    if score >= THRESHOLD_ALERT:
        return "ALERT"
    if score >= THRESHOLD_WATCHING:
        return "WATCHING"
    return "NORMAL"


def _aave_line(profile: dict) -> Optional[str]:
    mod = profile.get("aave_modifier", 1.0)
    if mod >= 1.5:
        return "⚡ Aave      Flash loan detected same block → modifier ×1.5"
    if mod >= 1.3:
        return "⚡ Aave      Collateral dump detected (<15 min) → modifier ×1.3"
    if mod >= 1.2:
        return "⚡ Aave      Open borrow fresh (<15 min, ≥$10K) → modifier ×1.2"
    return None


def _wash_detail(profile: dict) -> str:
    label = profile.get("wash_label", "MONITORING")
    ratio = profile.get("wash_ratio", 0.0)
    net   = profile.get("net_flow", 0.0)
    conc  = profile.get("concentration", 0.0)
    detail = f"ratio {ratio:.1f}× | net_flow {net:.2f} | concentration {conc:.2f}"
    return f"{label}\n             {detail}"


def _corr_label(corroboration: int) -> str:
    return {
        1: "Agni: ANOMALY | Moe: NORMAL | Fluxion: NORMAL",
        2: "2 DEX flagged — Market Event (corr. ×0.6)",
        3: "ALL 3 DEX flagged — Market Event (corr. ×0.3)",
    }.get(corroboration, "")


# ── ANOMALY alert builder ─────────────────────────────────────────────────────

def build_anomaly_alert(
    pool_name: str,
    dex_name: str,
    score: float,
    l1_score: float,
    l2_score: float,
    l3_score: float,
    l1_detail: str,
    profile: dict,
    prediction: Optional[dict] = None,
    tx_hashes: Optional[list] = None,
) -> str:
    wallet = profile.get("wallet", "")
    agent_type = profile.get("agent_type", "")
    aave_mod = profile.get("aave_modifier", 1.0)
    cycle_count = profile.get("cycle_count", 0)
    wash_label = profile.get("wash_label", "")

    if score >= THRESHOLD_HIGH_CONF:
        header = "🚨 High confidence anomaly detected on Mantle."
    else:
        header = "⚠️ Heads up. Something suspicious is happening on Mantle."

    pool_display = f"{dex_name.upper()} pool {pool_name}"

    detections = []
    if wash_label and wash_label not in ("CLEAN", "MONITORING"):
        detections.append("✅ Wash trading pattern")
    if agent_type == "Suspicious Coordination":
        detections.append("✅ Coordinated wallet activity")
    if cycle_count > 0:
        detections.append("✅ Repeated buy/sell cycles detected")
    if aave_mod >= 1.3:
        detections.append("✅ Aave lending activity linked to this pool")
    if l3_score > 0:
        detections.append("✅ Multi-protocol interaction pattern")
    if not detections:
        detections.append("✅ Statistical anomaly in trading volume")

    dump_window = prediction.get("dump_window_min", 90) if prediction else 90
    detection_block = "\n".join(detections)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    wallet_line = ""
    if wallet:
        w_short = wallet[:6] + ".." + wallet[-4:]
        wallet_line = f'\n🔍 Suspect wallet: <a href="https://mantlescan.xyz/address/{wallet}">{w_short}</a>'

    tx_block = ""
    if tx_hashes:
        tx_lines = ["", "🔗 Transactions"]
        for h in tx_hashes[:3]:
            tx_lines.append(f'<a href="https://mantlescan.xyz/tx/{h}">{h[:10]}...</a>')
        tx_block = "\n".join(tx_lines)

    text = f"""{header}

{pool_display} is showing signs of market manipulation.

What we detected
{detection_block}{wallet_line}

Be careful.
→ Avoid opening positions in this pool right now
→ Watch this pool for the next {dump_window} minutes
→ Full report: https://madmantle.vercel.app{tx_block}

⏱ {now_str}"""

    return text

# ── SMART MONEY alert builder ─────────────────────────────────────────────────
def build_smart_money_alert(
    wallet: str,
    pool_name: str,
    dex_name: str,
    roi_7d: float,
    smart_score: float,
    agent_type: str,
    archetype: str,
    rep_score: float,
    volume_usd: float,
    tx_count: int,
    erc8004_token_id: Optional[int] = None,
    aave_modifier: float = 1.0,
) -> str:
    wallet_short = wallet[:6] + ".." + wallet[-4:] if len(wallet) > 10 else wallet
    roi_sign = "+" if roi_7d >= 0 else ""
    is_agent = agent_type in ("Registered Agent", "SMART MONEY", "Probable Automation")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mantlescan = f"https://mantlescan.xyz/address/{wallet}"

    signals = []
    if roi_7d and roi_7d >= 10:
        signals.append(f"✅ {roi_sign}{roi_7d:.1f}% ROI in the last 7 days")
    signals.append("✅ Clean trading pattern — no wash detected")
    if is_agent:
        signals.append("✅ Identified as an AI agent on Mantle")
    if volume_usd >= 10000:
        signals.append(f"✅ ${volume_usd:,.0f} volume in current window")
    signals_block = "\n".join(signals)

    text = f"""💡 A smart wallet just moved on Mantle.

<a href="{mantlescan}">{wallet_short}</a> is showing strong performance signals.

What we know
{signals_block}

What you can do
→ <a href="{mantlescan}">Track this wallet on MantleScan</a>
→ Monitor which pools they enter next
→ Dashboard: https://madmantle.vercel.app

⏱ {now_str}"""

    return text

# ── DAILY DIGEST builder ──────────────────────────────────────────────────────
def build_daily_digest(
    scan_count: int,
    alert_count: int,
    watching_count: int,
    top_wallets: list,
    top_pools: list,
    total_volume_usd: float,
    phase1_active: bool = False,
    start_date: str = "",
) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "📋 MAD Daily Report — Mantle Network",
        "",
        "Here's what happened today.",
        "",
        "📊 Activity",
        f"Scans completed {scan_count}",
        f"Anomalies detected {alert_count}",
        f"Currently watching {watching_count}",
        f"Total volume ${total_volume_usd:,.0f}",
    ]

    if top_pools:
        lines += ["", "🏊 Most active pools"]
        for i, p in enumerate(top_pools[:5], 1):
            pool = p.get("pool_name", "unknown")
            dex = p.get("dex", "").upper()
            score = p.get("s_dex", 0.0)
            vol = p.get("volume_usd", 0.0)
            lines.append(f"{i}. {pool} ({dex}) — Score: {score:.0f} | Vol: ${vol:,.0f}")

    if top_wallets:
        lines += ["", "🧠 Top performing wallets"]
        for i, w in enumerate(top_wallets[:5], 1):
            addr = w.get("wallet", w.get("address", ""))
            addr_s = addr[:6] + ".." + addr[-4:] if len(addr) > 10 else addr
            roi = w.get("roi_7d", 0.0) or 0.0
            atype = w.get("agent_type", w.get("risk_label", ""))
            roi_sign = "+" if roi >= 0 else ""
            url = f"https://mantlescan.xyz/address/{addr}"
            lines.append(f'{i}. <a href="{url}">{addr_s}</a> — {roi_sign}{roi:.1f}% ROI | {atype}')

    lines += ["", "https://madmantle.vercel.app", f"⏱ {now_str}"]
    return "\n".join(lines)

# ── Broadcast functions ───────────────────────────────────────────────────────

async def broadcast_signal(signal: dict, verbose: bool = False) -> bool:
    alert_level = signal.get("alert_level", "none")
    if alert_level == "none":
        return False

    s_final      = signal.get("s_final", 0.0)
    dex          = signal.get("dex", "unknown").upper()
    pool_address = signal.get("pool_address", "")
    pool_name    = pool_address[:6] + ".." + pool_address[-4:] if len(pool_address) > 10 else pool_address
    l1_score     = signal.get("l1_score", 0.0)
    l2_score     = signal.get("l2_score", 0.0)
    l3_score     = signal.get("l3_score", 0.0)
    l1_methods   = signal.get("l1_methods", [])
    top_wallets  = signal.get("top_wallets", [])
    corroboration = signal.get("corroboration", 1)
    tx_hashes    = signal.get("tx_hashes", [])

    l1_detail = "+".join(
        m.get("method", "") for m in l1_methods if isinstance(m, dict)
    ) or "StatScore"

    profile: dict = {}
    if top_wallets:
        profile = top_wallets[0] if isinstance(top_wallets[0], dict) else {}
    profile.setdefault("wallet", pool_address)
    profile.setdefault("corroboration", corroboration)

    prediction = signal.get("prediction") if verbose else None
    agent_type = profile.get("agent_type", "UNKNOWN WALLET")

    if agent_type == "SMART MONEY" and alert_level == "watching":
        text = build_smart_money_alert(
            wallet           = profile.get("wallet", pool_address),
            pool_name        = pool_name,
            dex_name         = dex,
            roi_7d           = profile.get("roi_7d", 0.0) or 0.0,
            smart_score      = profile.get("smart_score", 0.0),
            agent_type       = agent_type,
            archetype        = profile.get("archetype", "UNKNOWN"),
            rep_score        = profile.get("rep_score", 50.0),
            volume_usd       = signal.get("volume_usd", 0.0),
            tx_count         = len(tx_hashes),
            erc8004_token_id = profile.get("erc8004_token_id"),
            aave_modifier    = profile.get("aave_modifier", 1.0),
        )
    else:
        text = build_anomaly_alert(
            pool_name  = pool_name,
            dex_name   = dex,
            score      = s_final,
            l1_score   = l1_score,
            l2_score   = l2_score,
            l3_score   = l3_score,
            l1_detail  = l1_detail,
            profile    = profile,
            prediction = prediction,
            tx_hashes  = tx_hashes or None,
        )

    if DEMO_MODE:
        text = "[DEMO] ⚠️\n" + text

    payload = {
        "text":                     text,
        "disable_web_page_preview": True,
    }

    success = await _rate_limited_send(payload)
    if success:
        logger.info("[alerter] ANOMALY alert sent — level=%s s_final=%.1f", alert_level, s_final)
    return success


async def broadcast_smart_money(profile: dict, pool_name: str, dex_name: str, volume_usd: float, tx_count: int) -> bool:
    text = build_smart_money_alert(
        wallet           = profile.get("wallet", ""),
        pool_name        = pool_name,
        dex_name         = dex_name,
        roi_7d           = profile.get("roi_7d", 0.0) or 0.0,
        smart_score      = profile.get("smart_score", 0.0),
        agent_type       = profile.get("agent_type", "SMART MONEY"),
        archetype        = profile.get("archetype", "UNKNOWN"),
        rep_score        = profile.get("rep_score", 50.0),
        volume_usd       = volume_usd,
        tx_count         = tx_count,
        erc8004_token_id = profile.get("erc8004_token_id"),
        aave_modifier    = profile.get("aave_modifier", 1.0),
    )

    payload = {
        "chat_id":                  TELEGRAM_CHANNEL_ID,
        "text":                     text,
        "disable_web_page_preview": True,
    }

    success = await _rate_limited_send(payload)
    if success:
        logger.info("[alerter] SMART_MONEY alert sent — wallet=%s", profile.get("wallet", ""))
    return success


async def broadcast_digest(
    scan_count: int = 0,
    alert_count: int = 0,
    watching_count: int = 0,
    top_wallets: Optional[list] = None,
    top_pools: Optional[list] = None,
    total_volume_usd: float = 0.0,
    phase1_active: bool = False,
    start_date: str = "",
) -> bool:
    if DEMO_MODE:
        logger.info("[alerter] Demo mode — digest skipped")
        return False

    if scan_count == 0:
        try:
            from database import get_digest_stats
            stats            = get_digest_stats()
            scan_count       = stats.get("scan_count", 0)
            alert_count      = stats.get("alert_count", 0)
            watching_count   = stats.get("watching_count", 0)
            top_wallets      = stats.get("top_wallets", [])
            top_pools        = stats.get("top_pools", [])
            total_volume_usd = stats.get("total_volume_usd", 0.0)
            phase1_active    = stats.get("phase1_active", False)
            start_date       = stats.get("start_date", "")
        except Exception as e:
            logger.warning("[alerter] get_digest_stats failed: %s", e)

    text = build_daily_digest(
        scan_count       = scan_count,
        alert_count      = alert_count,
        watching_count   = watching_count,
        top_wallets      = top_wallets or [],
        top_pools        = top_pools or [],
        total_volume_usd = total_volume_usd,
        phase1_active    = phase1_active,
        start_date       = start_date,
    )

    payload = {
        "chat_id":                  TELEGRAM_CHANNEL_ID,
        "text":                     text,
        "disable_web_page_preview": True,
    }

    success = await _rate_limited_send(payload)
    if success:
        logger.info("[alerter] DAILY_DIGEST sent")
    return success