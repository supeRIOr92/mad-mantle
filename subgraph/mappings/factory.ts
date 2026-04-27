// mappings/factory.ts — Factory event handlers
// Handles: AgniFactory.PoolCreated + MoeLBFactory.LBPairCreated

import { BigDecimal, BigInt } from "@graphprotocol/graph-ts";
import { PoolCreated as AgniPoolCreated } from "../generated/AgniFactory/AgniFactory";
import { LBPairCreated as MoePairCreated } from "../generated/MoeLBFactory/MoeLBFactory";
import { Pool } from "../generated/schema";

let ZERO_BD = BigDecimal.fromString("0");
let ZERO_BI = BigInt.fromI32(0);

function tokenSymbol(addr: string): string {
  if (addr == "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae") return "USDT";
  if (addr == "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9") return "USDC";
  if (addr == "0x78c1b0c915c4faa5fffa6cabf0219da63d7f4cb8") return "WMNT";
  if (addr == "0xdeaddeaddeaddeaddeaddeaddeaddeaddead1111") return "WETH";
  if (addr == "0xcda86a272531e8640cd7f1a92c01839911b90bb0") return "mETH";
  return addr.slice(0, 8) + "...";
}

export function handleAgniPoolCreated(event: AgniPoolCreated): void {
  let address = event.address.toHexString().toLowerCase();
  let pool = Pool.load(address);
  if (pool == null) {
    pool = new Pool(address);
    pool.dex = "agni";
    pool.token0 = event.params.token0.toHexString().toLowerCase();
    pool.token1 = event.params.token1.toHexString().toLowerCase();
    pool.token0Symbol = tokenSymbol(pool.token0);
    pool.token1Symbol = tokenSymbol(pool.token1);
    pool.feeTier = event.params.fee as i32;
    pool.createdAt = event.block.timestamp;
    pool.totalVolumeUSD = ZERO_BD;
    pool.txCount = ZERO_BI;
    pool.lastSwapAt = ZERO_BI;
    pool.save();
  }
}

export function handleMoePairCreated(event: MoePairCreated): void {
  let address = event.params.LBPair.toHexString().toLowerCase();
  let pool = Pool.load(address);
  if (pool == null) {
    pool = new Pool(address);
    pool.dex = "moe";
    pool.token0 = event.params.tokenX.toHexString().toLowerCase();
    pool.token1 = event.params.tokenY.toHexString().toLowerCase();
    pool.token0Symbol = tokenSymbol(pool.token0);
    pool.token1Symbol = tokenSymbol(pool.token1);
    pool.feeTier = event.params.binStep.toI32();
    pool.createdAt = event.block.timestamp;
    pool.totalVolumeUSD = ZERO_BD;
    pool.txCount = ZERO_BI;
    pool.lastSwapAt = ZERO_BI;
    pool.save();
  }
}