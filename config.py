import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# ── RPC & Subgraph ────────────────────────────────────
MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
AAVE_POOL_ADDRESS = os.getenv("AAVE_POOL_ADDRESS", "0x458F293454fE0d67EC0655f3672301301DD51422")
SUBGRAPH_URL = os.getenv("SUBGRAPH_URL", "https://api.goldsky.com/api/public/project_cmogywldzn5pt01wu4yx027en/subgraphs/mad-mantle/v1.1.0/gn")

# ── APIs ──────────────────────────────────────────────
MANTLESCAN_API_KEY = os.getenv("MANTLESCAN_API_KEY")
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"

# ── Contract Addresses ────────────────────────────────
ERC8004_IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
ERC8004_REPUTATION_REGISTRY = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

AGNI_FACTORY = "0x25780dc8Fc3cfBD75F33bFDAB65e969b603b2035"
MOE_LB_FACTORY = "0xa6630671775c4EA2743840F9A5016dCf2A104054"
FLUXION_POOL = "0x560d064493de5a23e72ed916caf92ec6e8924948"

# ── Detection Parameters ──────────────────────────────
# L1
ZSCORE_PRIMARY_WINDOW_MIN = 15 # minutes
ZSCORE_SECONDARY_WINDOW_MIN = 60 # minutes
ZSCORE_ROLLING_BASELINE_DAYS = 7
BOLLINGER_PERIOD = 20 # candles
BOLLINGER_SIGMA_BASELINE = 2.0
BOLLINGER_SIGMA_ADAPTIVE = 2.5 # if daily_range > 3x 7d avg
BOLLINGER_ADAPTIVE_TRIGGER = 3.0 # multiplier vs 7d avg range
POISSON_BASELINE_DAYS = 7
RATE_OF_CHANGE_MULTIPLIER = 5.0 # 5x 7d avg tx count

# L2
WASH_RATIO_EPSILON = 1e-9
SENDER_CONCENTRATION_TOP_N = 5 # top-5 wallets
WASH_RATIO_HIGH_THRESHOLD = 10.0 # ratio > 10x = full 25 pts
WASH_RATIO_MID_THRESHOLD = 5.0 # ratio 5-10x = partial pts
ERC8004_HIGH_RISK_THRESHOLD = 30 # score < 30 = high risk multiplier

# L3
L3_TRIGGER_THRESHOLD = 50 # L1+L2 combined > 50 to run L3
CYCLE_WINDOW_MIN = (5, 60) # A→B→A must complete in 5-60 min
CYCLE_MAX_HOPS = 4 # max cycle length
BENFORD_PVALUE_THRESHOLD = 0.05 # p < 0.05 = significant

# ── Scoring ───────────────────────────────────────────
L1_MAX = 60
L2_MAX = 55
L3_MAX = 50
SCORE_DENOMINATOR = 165 # L1+L2+L3 max

CORROBORATION_MODIFIER = {1: 1.0, 2: 0.6, 3: 0.3}
DEXSCREENER_WEIGHT_FLOOR = 0.05 # w < 5% → auto-zero

# ── Thresholds ────────────────────────────────────────
THRESHOLD_WATCHING = 41
THRESHOLD_ALERT = 71
THRESHOLD_HIGH_CONF = 86
THRESHOLD_PHASE1 = 80 # first 7 days — conservative
PHASE1_DAYS = 7

# ── Scheduler ────────────────────────────────────────
POLL_DEFAULT_MIN = 15
POLL_WATCH_MIN = 5
POLL_WATCH_TRIGGER = 70 # S_final > 70 → watch mode
POLL_WATCH_DEESCALATE = 50 # S_final < 50 for 2 polls → back to default
DIGEST_HOUR_UTC = 0 # daily digest at 00:00 UTC

# ── Capital Flow ──────────────────────────────────────
CAPITAL_FLOW_SINGLE_MULTIPLIER = 5.0 # single swap > 5x pool avg
CAPITAL_FLOW_COORDINATED_USD = 10000 # 3+ wallets combined > $10K in 15min
CAPITAL_FLOW_COORDINATED_WALLETS = 3

# ── Database ──────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "mad.db")
