"use client";
import { useEffect, useState } from "react";
import { supabase, type Wallet } from "@/lib/supabase";

function agentBadge(type: string) {
if (type === "CONFIRMED AGENT") return "text-green-400";
if (type === "PROBABLE AGENT") return "text-cyan-400";
if (type === "MANIPULATOR") return "text-red-400";
if (type === "SMART MONEY") return "text-purple-400";
return "text-slate-400";
}

export default function Panel4SmartMoney() {
const [wallets, setWallets] = useState<Wallet[]>([]);

useEffect(() => {
const fetch = () => {
supabase
.from("wallet_profile")
.select("*")
.order("smart_score", { ascending: false, nullsFirst: false })
.limit(10)
.then(({ data }) => { if (data) setWallets(data as Wallet[]); });
};
fetch();

const channel = supabase
.channel("panel4-wallets")
.on("postgres_changes", { event: "*", schema: "public", table: "wallet_profile" },
() => fetch()
)
.subscribe();

return () => { supabase.removeChannel(channel); };
}, []);

const manipulators = wallets.filter(w => w.agent_type === "MANIPULATOR");
const legit = wallets.filter(w => w.agent_type !== "MANIPULATOR");
return (
<div className="panel h-full">
<div className="mb-2">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Smart Money Leaderboard</h2>
<p className="text-[10px] text-slate-500 mt-0.5">
7d rolling — smart_score = (1+ROI) × (1–wash_penalty) × rep/100 [v9.0]
</p>
</div>

<div className="overflow-x-auto">
<table className="w-full text-[11px]">
<thead>
<tr className="text-slate-500 border-b border-mad-border">
<th className="text-left pb-1 pr-2">#</th>
<th className="text-left pb-1 pr-2">Wallet</th>
<th className="text-left pb-1 pr-2">Type</th>
<th className="text-right pb-1 pr-2">Score</th>
<th className="text-right pb-1 pr-2">ROI 7d</th>
<th className="text-right pb-1 pr-2">Wash</th>
<th className="text-right pb-1">Vol</th>
</tr>
</thead>
<tbody>
{legit.slice(0, 5).map((w, i) => (
<tr key={w.address} className="border-b border-mad-border/50 hover:bg-mad-bg transition-colors">
<td className="py-1 pr-2 text-slate-500">#{i + 1}</td>
<td className="py-1 pr-2 font-mono text-white">
{w.address.slice(0, 6)}..{w.address.slice(-4)}
{w.agent_token_id && <span className="text-slate-500 ml-1">#{w.agent_token_id}</span>}
</td>
<td className={`py-1 pr-2 font-semibold ${agentBadge(w.agent_type)}`}>{w.agent_type}</td>
<td className="py-1 pr-2 text-right text-purple-400">{(w.smart_score || 0).toFixed(3)}</td>
<td className="py-1 pr-2 text-right text-green-400">
{w.roi_7d != null ? `+${w.roi_7d.toFixed(1)}%` : "—"}
</td>
<td className="py-1 pr-2 text-right text-slate-300">{w.wash_ratio?.toFixed(1)}×</td>
<td className="py-1 text-right text-slate-300">
${((w.total_volume_usd || 0) / 1000).toFixed(0)}K
</td>
</tr>
))}

{manipulators.slice(0, 2).map((w) => (
<tr key={w.address} className="bg-red-500/5 border-b border-red-500/20">
<td className="py-1 pr-2 text-red-500">⛔</td>
<td className="py-1 pr-2 font-mono text-red-400">
{w.address.slice(0, 6)}..{w.address.slice(-4)}
</td>
<td className="py-1 pr-2 font-semibold text-red-400">MANIPULATOR</td>
<td className="py-1 pr-2 text-right text-red-400">0.000</td>
<td className="py-1 pr-2 text-right text-red-400">
{w.roi_7d != null ? `+${w.roi_7d.toFixed(1)}%*` : "—"}
</td>
<td className="py-1 pr-2 text-right text-red-400">{w.wash_ratio?.toFixed(1)}×</td>
<td className="py-1 text-right text-red-400">
${((w.total_volume_usd || 0) / 1000).toFixed(0)}K
</td>
</tr>
))}
</tbody>
</table>
{manipulators.length > 0 && (
<p className="text-[10px] text-red-500/70 mt-1">* artificial ROI — EXCLUDED from leaderboard</p>
)}
</div>
</div>
);
}
