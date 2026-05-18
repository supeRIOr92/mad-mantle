import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# ── RPC & Subgraph ────────────────────────────────────
MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
RPC_BLOCK_LOOKBACK = int(os.getenv("RPC_BLOCK_LOOKBACK", "2000"))
AAVE_POOL_ADDRESS = os.getenv("AAVE_POOL_ADDRESS", "0x458F293454fE0d67EC0655f3672301301DD51422")

# ── APIs ──────────────────────────────────────────────
MANTLESCAN_API_KEY = os.getenv("MANTLESCAN_API_KEY")
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"

# ── Supabase ──────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ── Contract Addresses ────────────────────────────────
ERC8004_IDENTITY_REGISTRY  = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
ERC8004_REPUTATION_REGISTRY = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

AGNI_FACTORY  = "0x25780dc8Fc3cfBD75F33bFDAB65e969b603b2035"
MOE_LB_FACTORY = "0xa6630671775c4EA2743840F9A5016dCf2A104054"
FLUXION_POOL  = "0x560d064493de5a23e72ed916caf92ec6e8924948"

# Stablecoins on Mantle (chainId 5000) — used for amountUSD calculation in swap decode
# Source: token-list.mantle.xyz (verified)
MANTLE_STABLECOINS = {
"0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9", # USDC
"0x201eba5cc46d216ce6dc03f6a759e8e766e956ae", # USDT
"0x5d3a1ff2b6bab83b63cd9ad0787074081a52ef34", # USDe
"0x0994206dfe8de6ec6920ff4d779b0d950605fb53", # crvUSD
}

# ── Detection Parameters ──────────────────────────────
# L1
ZSCORE_PRIMARY_WINDOW_MIN    = 15
ZSCORE_SECONDARY_WINDOW_MIN  = 60
ZSCORE_ROLLING_BASELINE_DAYS = 7
BOLLINGER_PERIOD             = 20
BOLLINGER_SIGMA_BASELINE     = 2.0
BOLLINGER_SIGMA_ADAPTIVE     = 2.5   # if daily_range > 3x 7d avg
BOLLINGER_ADAPTIVE_TRIGGER   = 3.0
POISSON_BASELINE_DAYS        = 7
RATE_OF_CHANGE_MULTIPLIER    = 5.0

# L2 — Wash ratio 3-way gate (v2.0)
WASH_RATIO_EPSILON           = 1e-9
WASH_RATIO_HIGH_THRESHOLD    = 10.0   # ratio > 10x = full 25 pts
WASH_RATIO_MID_THRESHOLD     = 5.0    # ratio 5-10x = partial pts
WASH_NET_FLOW_CIRCULAR       = 0.05   # net_flow < 0.05 = circular (suspicious)
WASH_NET_FLOW_DIRECTIONAL    = 0.30   # net_flow > 0.30 = directional (likely bot/arb)
WASH_CONCENTRATION_THRESHOLD = 0.60   # top-wallet concentration > 60%
SENDER_CONCENTRATION_TOP_N   = 5
ERC8004_HIGH_RISK_THRESHOLD  = 30     # rep score < 30 = high risk

# L3
L3_TRIGGER_THRESHOLD         = 50
CYCLE_WINDOW_MIN             = (5, 60)
CYCLE_MAX_HOPS               = 4
BENFORD_PVALUE_THRESHOLD     = 0.05

# ── Scoring ───────────────────────────────────────────
L1_MAX           = 60
L2_MAX           = 55
L3_MAX           = 50
SCORE_DENOMINATOR = 165

CORROBORATION_MODIFIER = {1: 1.0, 2: 0.6, 3: 0.3}
DEXSCREENER_WEIGHT_FLOOR = 0.05
FALLBACK_DISCOUNT = 0.5 # prior weight discount when DexScreener coverage missing

# ── Aave Detection Windows ────────────────────────────────
AAVE_FLASH_LOAN_WINDOW_BLOCKS = 1 # same block only (per-wallet, legacy)
AAVE_COLLATERAL_DUMP_WINDOW_MIN = 15
AAVE_OPEN_BORROW_MIN_USD = 10_000
AAVE_OPEN_BORROW_FRESH_MIN = 15
AAVE_MODIFIER_CAP = 1.5

# — Pool-level signal (independen from per-wallet cache)
AAVE_SIGNAL_WINDOW_BLOCKS = 50 # ~100 secs in Mantle (~2s/block)
AAVE_ALPHA = 0.3 # fixed, conservative, defensible
AAVE_HARD_GATE_THRESHOLD = 20.0 # s_moe < 20.0 → aave_signal_effective = 0

# ── Thresholds ────────────────────────────────────────
THRESHOLD_WATCHING  = 41
THRESHOLD_ALERT     = 71
THRESHOLD_HIGH_CONF = 86
THRESHOLD_PHASE1    = 80   # first 7 days — conservative
PHASE1_DAYS         = 7

# ── Scheduler ─────────────────────────────────────────
POLL_DEFAULT_MIN       = 15
POLL_WATCH_MIN         = 5
POLL_WATCH_TRIGGER     = 70
POLL_WATCH_DEESCALATE  = 50
DIGEST_HOUR_UTC        = 8   # daily digest at 08:00 UTC

# ── Capital Flow ──────────────────────────────────────
CAPITAL_FLOW_SINGLE_MULTIPLIER     = 5.0
CAPITAL_FLOW_COORDINATED_USD       = 10_000
CAPITAL_FLOW_COORDINATED_WALLETS   = 3

# ── Smart Money ───────────────────────────────────────
SMART_MONEY_ROI_MIN          = 15.0   # ROI 7d > 15% = smart money candidate
SMART_MONEY_WASH_MAX         = 3.0    # wash_ratio < 3x = clean
SMART_MONEY_HEURISTIC_MIN    = 2      # need >= 2 heuristics to be PROBABLE AGENT
AGENT_HIGH_FREQ_TX_MIN       = 10     # >= 10 swaps in window
AGENT_ROUND_AMOUNT_PCT       = 0.50   # > 50% of amounts are round numbers
AGENT_EXEC_TIME_MAX_SEC      = 3      # < 3s execution time
AGENT_CV_MAX                 = 0.10   # coefficient of variation < 0.10

# ── Risk Prediction Engine (v2.0) ─────────────────────
PREDICTOR_TOP_K              = 5      # top-K nearest neighbors
PREDICTOR_MIN_EVENTS         = 3      # < 3 events = LOW confidence
PREDICTOR_CONFIDENCE_SCALE   = 10     # confidence = min(similar / 10, 1.0)
FEATURE_CYCLE_NORM           = 5.0    # cycle_count / 5 -> 0-1
FEATURE_AAVE_NORM_OFFSET     = 1.0    # (aave_mod - 1.0) / 0.5 -> 0-1
FEATURE_AAVE_NORM_SCALE      = 0.5
FEATURE_TX_DENSITY_NORM      = 10.0   # tx_per_minute / 10 -> 0-1

# ── Database ──────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "mad.db")

DEX_WEIGHTS = {
    "agni":    0.40,
    "moe":     0.45,
    "fluxion": 0.15,
}

# ── Chain ─────────────────────────────────────────────
MANTLE_CHAIN_ID = 5000
AGENT_COUNT_MANTLE = 92

# ── Demo Mode ─────────────────────────────────────────
DEMO_MODE = os.getenv("APP_MODE", "live") == "demo"
TELEGRAM_DEMO_CHANNEL_ID = os.getenv("TELEGRAM_DEMO_CHANNEL_ID", "")