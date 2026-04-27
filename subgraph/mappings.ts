// mappings.ts — MAD: Mantle Anomaly Detector
// Unified event handlers: Agni Finance + Merchant Moe LB 2.2 + Fluxion (UniV3)
// Chain: Mantle (chain_id 5000)
// amountUSD: stablecoin pairs only — non-stable resolved by detector.py via DexScreener

import { BigDecimal, BigInt, log } from "@graphprotocol/graph-ts";

import { PoolCreated as AgniPoolCreated, Swap as AgniSwapEvent } from "../generated/AgniPool/AgniPool";
import { PoolCreated as FluxionPoolCreated, Swap as FluxionSwapEvent } from "../generated/FluxionPool/FluxionPool";
import { LBPairCreated as MoePairCreated, Swap as MoeSwapEvent } from "../generated/MoeLBPair/MoeLBPair";

import { Swap, Pool, Wallet, VolumeBucket, DailyPoolSnapshot } from "../generated/schema";

// ── Constants ──────────────────────────────────────────────────────────────

let ZERO_BD = BigDecimal.fromString("0");
let ZERO_BI = BigInt.fromI32(0);
let ONE_BI = BigInt.fromI32(1);
let SCALE = BigDecimal.fromString("1000000000000000000"); // 1e18
let SCALE_6 = BigDecimal.fromString("1000000"); // 1e6 (USDT/USDC)
let BUCKET_SIZE = BigInt.fromI32(900); // 15 min in seconds

// Stablecoin addresses on Mantle (lowercase) — only these resolve amountUSD in-subgraph
// All other pairs: amountUSD = 0, resolved by detector.py at runtime via DexScreener
let STABLES: string[] = [
  "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae", // USDT
  "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9", // USDC
  "0x0a3bb08b3a15a19b4de82f8acfc862606fb69a2d", // USDT (Orbit Bridge)
];

// ── Helpers ────────────────────────────────────────────────────────────────

function isStable(addr: string): bool {
  for (let i = 0; i < STABLES.length; i++) {
    if (STABLES[i] == addr) return true;
  }
  return false;
}

function tokenSymbol(addr: string): string {
  if (addr == "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae") return "USDT";
  if (addr == "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9") return "USDC";
  if (addr == "0x78c1b0c915c4faa5fffa6cabf0219da63d7f4cb8") return "WMNT";
  if (addr == "0xdeaddeaddeaddeaddeaddeaddeaddeaddead1111") return "WETH";
  if (addr == "0xcda86a272531e8640cd7f1a92c01839911b90bb0") return "mETH";
  return addr.slice(0, 8) + "...";
}

function resolveAmountUSD(
  token0: string,
  token1: string,
  amount0Abs: BigDecimal,
  amount1Abs: BigDecimal,
  decimals0: i32,
  decimals1: i32
): BigDecimal {
  // Only resolve if one side is a known stablecoin
  // Scale by decimals to get human-readable amount
  if (isStable(token1)) {
    let scale = decimals1 == 6 ? SCALE_6 : SCALE;
    return amount1Abs.div(scale);
  }
  if (isStable(token0)) {
    let scale = decimals0 == 6 ? SCALE_6 : SCALE;
    return amount0Abs.div(scale);
  }
  // Non-stable pair: return 0, detector.py resolves via DexScreener
  return ZERO_BD;
}

function getOrCreatePool(
  address: string,
  dex: string,
  token0: string,
  token1: string,
  fee: i32,
  timestamp: BigInt
): Pool {
  let pool = Pool.load(address);
  if (pool == null) {
    pool = new Pool(address);
    pool.dex = dex;
    pool.token0 = token0;
    pool.token1 = token1;
    pool.token0Symbol = tokenSymbol(token0);
    pool.token1Symbol = tokenSymbol(token1);
    pool.feeTier = fee;
    pool.createdAt = timestamp;
    pool.totalVolumeUSD = ZERO_BD;
    pool.txCount = ZERO_BI;
    pool.lastSwapAt = ZERO_BI;
    pool.save();
  }
  return pool as Pool;
}

function getOrCreateWallet(address: string, timestamp: BigInt): Wallet {
  let wallet = Wallet.load(address);
  if (wallet == null) {
    wallet = new Wallet(address);
    wallet.firstSeenAt = timestamp;
    wallet.lastSeenAt = timestamp;
    wallet.totalVolumeUSD = ZERO_BD;
    wallet.txCount = ZERO_BI;
    wallet.isAgent = false;
    wallet.agentTokenId = null;
    wallet.agentReputation = null;
    wallet.save();
  } else {
    wallet.lastSeenAt = timestamp;
    wallet.save();
  }
  return wallet as Wallet;
}

function updateBucket(
  poolId: string,
  dex: string,
  timestamp: BigInt,
  amountUSD: BigDecimal
): void {
  let bucketStart = timestamp.div(BUCKET_SIZE).times(BUCKET_SIZE);
  let id = poolId + "-" + dex + "-" + bucketStart.toString();
  let b = VolumeBucket.load(id);
  if (b == null) {
    b = new VolumeBucket(id);
    b.pool = poolId;
    b.dex = dex;
    b.bucketStart = bucketStart;
    b.volumeUSD = ZERO_BD;
    b.txCount = ZERO_BI;
    b.uniqueSenders = 0;
    b.topSenders = "[]";
  }
  b.volumeUSD = b.volumeUSD.plus(amountUSD);
  b.txCount = b.txCount.plus(ONE_BI);
  b.save();
}

function updateDaily(
  poolId: string,
  dex: string,
  timestamp: BigInt,
  amountUSD: BigDecimal
): void {
  let dayStart = timestamp.div(BigInt.fromI32(86400)).times(BigInt.fromI32(86400));
  let id = poolId + "-" + dex + "-day-" + dayStart.toString();
  let s = DailyPoolSnapshot.load(id);
  if (s == null) {
    s = new DailyPoolSnapshot(id);
    s.pool = poolId;
    s.dex = dex;
    s.dayStart = dayStart;
    s.volumeUSD = ZERO_BD;
    s.txCount = ZERO_BI;
    s.openPrice = ZERO_BD;
    s.closePrice = ZERO_BD;
    s.highPrice = ZERO_BD;
    s.lowPrice = BigDecimal.fromString("999999999");
  }
  s.volumeUSD = s.volumeUSD.plus(amountUSD);
  s.txCount = s.txCount.plus(ONE_BI);
  s.save();
}

// ── Agni Finance ───────────────────────────────────────────────────────────

export function handleAgniPoolCreated(event: AgniPoolCreated): void {
  getOrCreatePool(
    event.address.toHexString().toLowerCase(), "agni",
    event.params.token0.toHexString().toLowerCase(),
    event.params.token1.toHexString().toLowerCase(),
    event.params.fee as i32,
    event.block.timestamp
  );
}

export function handleAgniSwap(event: AgniSwapEvent): void {
  let poolAddress = event.address.toHexString().toLowerCase();
  let pool = Pool.load(poolAddress);
  if (pool == null) {
    log.warning("[MAD] AgniSwap: pool {} not found", [poolAddress]);
    return;
  }

  let timestamp = event.block.timestamp;
  let sender = event.params.sender.toHexString().toLowerCase();
  let recipient = event.params.recipient.toHexString().toLowerCase();
  let txHash = event.transaction.hash.toHexString();
  let logIndex = event.logIndex.toI32();

  // amount0/amount1 are int256 signed
  let a0raw = event.params.amount0.toBigDecimal();
  let a1raw = event.params.amount1.toBigDecimal();
  let a0abs = a0raw.lt(ZERO_BD) ? a0raw.neg() : a0raw;
  let a1abs = a1raw.lt(ZERO_BD) ? a1raw.neg() : a1raw;

  // Decimals: assume 18 unless stablecoin (6) — resolved in resolveAmountUSD
  let amountUSD = resolveAmountUSD(pool.token0, pool.token1, a0abs, a1abs, 18, 18);

  let swap = new Swap(txHash + "-" + logIndex.toString());
  swap.timestamp = timestamp;
  swap.blockNumber = event.block.number;
  swap.dex = "agni";
  swap.pool = poolAddress;
  swap.sender = sender;
  swap.recipient = recipient;
  swap.amountUSD = amountUSD;
  swap.amount0 = a0raw.div(SCALE);
  swap.amount1 = a1raw.div(SCALE);
  swap.sqrtPriceX96 = event.params.sqrtPriceX96;
  swap.tick = event.params.tick;
  swap.txHash = txHash;
  swap.logIndex = logIndex;
  swap.save();

  pool.totalVolumeUSD = pool.totalVolumeUSD.plus(amountUSD);
  pool.txCount = pool.txCount.plus(ONE_BI);
  pool.lastSwapAt = timestamp;
  pool.save();

  let w = getOrCreateWallet(sender, timestamp);
  w.totalVolumeUSD = w.totalVolumeUSD.plus(amountUSD);
  w.txCount = w.txCount.plus(ONE_BI);
  w.save();
  getOrCreateWallet(recipient, timestamp);

  updateBucket(poolAddress, "agni", timestamp, amountUSD);
  updateDaily(poolAddress, "agni", timestamp, amountUSD);
}

// ── Fluxion (UniV3 Fork) ───────────────────────────────────────────────────

export function handleFluxionPoolCreated(event: FluxionPoolCreated): void {
  getOrCreatePool(
    event.address.toHexString().toLowerCase(), "fluxion",
    event.params.token0.toHexString().toLowerCase(),
    event.params.token1.toHexString().toLowerCase(),
    event.params.fee as i32,
    event.block.timestamp
  );
}

export function handleFluxionSwap(event: FluxionSwapEvent): void {
  let poolAddress = event.address.toHexString().toLowerCase();
  let pool = Pool.load(poolAddress);
  if (pool == null) {
    log.warning("[MAD] FluxionSwap: pool {} not found", [poolAddress]);
    return;
  }

  let timestamp = event.block.timestamp;
  let sender = event.params.sender.toHexString().toLowerCase();
  let recipient = event.params.recipient.toHexString().toLowerCase();
  let txHash = event.transaction.hash.toHexString();
  let logIndex = event.logIndex.toI32();

  let a0raw = event.params.amount0.toBigDecimal();
  let a1raw = event.params.amount1.toBigDecimal();
  let a0abs = a0raw.lt(ZERO_BD) ? a0raw.neg() : a0raw;
  let a1abs = a1raw.lt(ZERO_BD) ? a1raw.neg() : a1raw;
  let amountUSD = resolveAmountUSD(pool.token0, pool.token1, a0abs, a1abs, 18, 18);

  let swap = new Swap(txHash + "-" + logIndex.toString());
  swap.timestamp = timestamp;
  swap.blockNumber = event.block.number;
  swap.dex = "fluxion";
  swap.pool = poolAddress;
  swap.sender = sender;
  swap.recipient = recipient;
  swap.amountUSD = amountUSD;
  swap.amount0 = a0raw.div(SCALE);
  swap.amount1 = a1raw.div(SCALE);
  swap.sqrtPriceX96 = event.params.sqrtPriceX96;
  swap.tick = event.params.tick;
  swap.txHash = txHash;
  swap.logIndex = logIndex;
  swap.save();

  pool.totalVolumeUSD = pool.totalVolumeUSD.plus(amountUSD);
  pool.txCount = pool.txCount.plus(ONE_BI);
  pool.lastSwapAt = timestamp;
  pool.save();

  let w = getOrCreateWallet(sender, timestamp);
  w.totalVolumeUSD = w.totalVolumeUSD.plus(amountUSD);
  w.txCount = w.txCount.plus(ONE_BI);
  w.save();
  getOrCreateWallet(recipient, timestamp);

  updateBucket(poolAddress, "fluxion", timestamp, amountUSD);
  updateDaily(poolAddress, "fluxion", timestamp, amountUSD);
}

// ── Merchant Moe LB 2.2 ───────────────────────────────────────────────────
// amountsIn/amountsOut: bytes32 — upper 128 bits = tokenX, lower 128 bits = tokenY
// amountUSD = 0 until bytes32 decode confirmed
// txCount tracked correctly — Poisson + RoC detection uses txCount, not volumeUSD

export function handleMoePairCreated(event: MoePairCreated): void {
  getOrCreatePool(
    event.params.LBPair.toHexString().toLowerCase(), "moe",
    event.params.tokenX.toHexString().toLowerCase(),
    event.params.tokenY.toHexString().toLowerCase(),
    event.params.binStep as i32,
    event.block.timestamp
  );
}

export function handleMoeSwap(event: MoeSwapEvent): void {
  let poolAddress = event.address.toHexString().toLowerCase();
  let pool = Pool.load(poolAddress);
  if (pool == null) {
    log.warning("[MAD] MoeSwap: pool {} not found", [poolAddress]);
    return;
  }

  let timestamp = event.block.timestamp;
  let sender = event.params.sender.toHexString().toLowerCase();
  let recipient = event.transaction.from.toHexString().toLowerCase();
  let txHash = event.transaction.hash.toHexString();
  let logIndex = event.logIndex.toI32();

  // TODO: decode bytes32 amountsIn/amountsOut after ABI confirmation
  // upper 128 bits = tokenX amount, lower 128 bits = tokenY amount
  // For now amountUSD = 0 — detector.py handles via DexScreener at runtime
  let amountUSD = ZERO_BD;

  let swap = new Swap(txHash + "-" + logIndex.toString());
  swap.timestamp = timestamp;
  swap.blockNumber = event.block.number;
  swap.dex = "moe";
  swap.pool = poolAddress;
  swap.sender = sender;
  swap.recipient = recipient;
  swap.amountUSD = amountUSD;
  swap.amount0 = ZERO_BD;
  swap.amount1 = ZERO_BD;
  swap.sqrtPriceX96 = null;
  swap.tick = null;
  swap.txHash = txHash;
  swap.logIndex = logIndex;
  swap.save();

  pool.txCount = pool.txCount.plus(ONE_BI);
  pool.lastSwapAt = timestamp;
  pool.save();

  let w = getOrCreateWallet(sender, timestamp);
  w.txCount = w.txCount.plus(ONE_BI);
  w.save();
  getOrCreateWallet(recipient, timestamp);

  // txCount tracked in bucket — Poisson + RoC detection still works
  updateBucket(poolAddress, "moe", timestamp, amountUSD);
  updateDaily(poolAddress, "moe", timestamp, amountUSD);
}