// @ts-nocheck

// mappings/index.ts — MAD unified handler entry point

import { BigDecimal, BigInt, Bytes, log } from "@graphprotocol/graph-ts";

import { PoolCreated as AgniPoolCreated } from "../generated/AgniFactory/AgniFactory";
import { Swap as AgniSwapEvent } from "../generated/AgniPool/AgniPool";
import { Swap as FluxionSwapEvent } from "../generated/FluxionPool/FluxionPool";
import { PoolCreated as FluxionPoolCreated } from "../generated/FluxionFactory/FluxionFactory";
import { LBPairCreated as MoePairCreated } from "../generated/MoeLBFactory/MoeLBFactory";
import { Swap as MoeSwapEvent } from "../generated/MoeLBPair/MoeLBPair";
import { Swap, Pool, Wallet, VolumeBucket, DailyPoolSnapshot } from "../generated/schema";
import { AgniPool as AgniPoolTemplate, MoeLBPair as MoeLBPairTemplate, FluxionPool as FluxionPoolTemplate } from "../generated/templates";

let ZERO_BD = BigDecimal.fromString("0");
let ZERO_BI = BigInt.fromI32(0);
let ONE_BI = BigInt.fromI32(1);
let SCALE = BigDecimal.fromString("1000000000000000000");
let SCALE_6 = BigDecimal.fromString("1000000");
let BUCKET_SIZE = BigInt.fromI32(900);

let STABLES: string[] = [
  "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae",
  "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9",
  "0x0a3bb08b3a15a19b4de82f8acfc862606fb69a2d",
  "0x111111d2bf19e43c34263401e0cad979ed1cdb61", // USDT1 (Fluxion)
  "0x779ded0c9e1022225f8e0630b35a9b54be713736", // USDT0 (Fluxion)
];

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
  if (addr == "0x111111d2bf19e43c34263401e0cad979ed1cdb61") return "USDT1";
  if (addr == "0x779ded0c9e1022225f8e0630b35a9b54be713736") return "USDT0";
  return addr.slice(0, 8) + "...";
}

function resolveAmountUSD(
  token0: string,
  token1: string,
  a0: BigDecimal,
  a1: BigDecimal
): BigDecimal {
  if (isStable(token1)) {
    let scale =
      token1 == "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae" ||
      token1 == "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9"
        ? SCALE_6
        : SCALE;
    return a1.div(scale);
  }
  if (isStable(token0)) {
    let scale =
      token0 == "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae" ||
      token0 == "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9"
        ? SCALE_6
        : SCALE;
    return a0.div(scale);
  }
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
  let w = Wallet.load(address);
  if (w == null) {
    w = new Wallet(address);
    w.firstSeenAt = timestamp;
    w.lastSeenAt = timestamp;
    w.totalVolumeUSD = ZERO_BD;
    w.txCount = ZERO_BI;
    w.isAgent = false;
    w.agentTokenId = null;
    w.save();
  } else {
    w.lastSeenAt = timestamp;
    w.save();
  }
  return w as Wallet;
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
  let dateStr = dayStart.toString();
  let id = poolId + "-" + dex + "-day-" + dateStr;

  let s = DailyPoolSnapshot.load(id);
  if (s == null) {
    s = new DailyPoolSnapshot(id);
    s.pool = poolId;
    s.dex = dex;
    s.date = dateStr;
    s.volumeUSD = ZERO_BD;
    s.txCount = ZERO_BI;
    s.highVolumeUSD = ZERO_BD;
    s.lowVolumeUSD = ZERO_BD;
  }

  s.volumeUSD = s.volumeUSD.plus(amountUSD);
  s.txCount = s.txCount.plus(ONE_BI);
  s.save();
}


// ── Agni Finance ──────────────────────────────────────────────────────────────

export function handleAgniPoolCreated(event: AgniPoolCreated): void {
  getOrCreatePool(
    event.address.toHexString().toLowerCase(),
    "agni",
    event.params.token0.toHexString().toLowerCase(),
    event.params.token1.toHexString().toLowerCase(),
    event.params.fee as i32,
    event.block.timestamp
  );
  AgniPoolTemplate.create(event.params.pool);
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

  let a0raw = event.params.amount0.toBigDecimal();
  let a1raw = event.params.amount1.toBigDecimal();
  let a0abs = a0raw.lt(ZERO_BD) ? a0raw.neg() : a0raw;
  let a1abs = a1raw.lt(ZERO_BD) ? a1raw.neg() : a1raw;
  let amountUSD = resolveAmountUSD(pool.token0, pool.token1, a0abs, a1abs);

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


// ── Merchant Moe LB 2.2 ──────────────────────────────────────────────────────

export function handleMoePairCreated(event: MoePairCreated): void {
  getOrCreatePool(
    event.params.LBPair.toHexString().toLowerCase(),
    "moe",
    event.params.tokenX.toHexString().toLowerCase(),
    event.params.tokenY.toHexString().toLowerCase(),
    event.params.binStep.toI32(),
    event.block.timestamp
  );
  MoeLBPairTemplate.create(event.params.LBPair);
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

  // Moe LB 2.2 — amountsIn/Out are Bytes32 packed
  // Big-endian layout: [tokenY: bytes 0-15][tokenX: bytes 16-31]
  let inBytes = event.params.amountsIn;
  let outBytes = event.params.amountsOut;

  let amountXIn = BigInt.fromUnsignedBytes(changetype<Bytes>(inBytes.slice(16)));
  let amountYIn = BigInt.fromUnsignedBytes(changetype<Bytes>(inBytes.slice(0, 16)));
  let amountXOut = BigInt.fromUnsignedBytes(changetype<Bytes>(outBytes.slice(16)));
  let amountYOut = BigInt.fromUnsignedBytes(changetype<Bytes>(outBytes.slice(0, 16)));

  let a0 = amountXIn.plus(amountXOut).toBigDecimal();
  let a1 = amountYIn.plus(amountYOut).toBigDecimal();
  let amountUSD = resolveAmountUSD(pool.token0, pool.token1, a0, a1);

  let swap = new Swap(txHash + "-" + logIndex.toString());
  swap.timestamp = timestamp;
  swap.blockNumber = event.block.number;
  swap.dex = "moe";
  swap.pool = poolAddress;
  swap.sender = sender;
  swap.recipient = recipient;
  swap.amountUSD = amountUSD;
  swap.amount0 = a0.div(SCALE);
  swap.amount1 = a1.div(SCALE);
  swap.sqrtPriceX96 = null;
  swap.tick = 0;
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
  updateBucket(poolAddress, "moe", timestamp, amountUSD);
  updateDaily(poolAddress, "moe", timestamp, amountUSD);
}

// ── Fluxion (UniV3 Fork) ──────────────────────────────────────────────────────
export function handleFluxionPoolCreated(event: FluxionPoolCreated): void {
  let poolAddress = event.params.pool.toHexString().toLowerCase();
  getOrCreatePool(
    poolAddress,
    "fluxion",
    event.params.token0.toHexString().toLowerCase(),
    event.params.token1.toHexString().toLowerCase(),
    event.params.fee as i32,
    event.block.timestamp
  );
  FluxionPoolTemplate.create(event.params.pool);
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
  let amountUSD = resolveAmountUSD(pool.token0, pool.token1, a0abs, a1abs);

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