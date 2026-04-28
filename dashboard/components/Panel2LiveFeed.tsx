"use client";
import { useEffect, useState } from "react";
import { supabase, type Signal } from "@/lib/supabase";

function feedEntry(s: Signal) {
const isAlert = s.alert_level === "alert" || s.alert_level === "high_conf";
const isWatching = s.alert_level === "watching";
const topWallet = s.top_wallets?.[0];
const isSmartMoney = topWallet?.agent_type === "SMART MONEY";

if (isSmartMoney) {
return {
type: "ALPHA",
cls: "border-cyan-500/40 bg-cyan-500/5",
badgeCls: "bg-cyan-500/20 text-cyan-400",
title: "Smart Money · " + s.dex?.toUpperCase(),
subtitle: `Wallet: ${topWallet?.wallet?.slice(0,6)}.. · $${((s.volume_usd||0)/1000).toFixed(1)}K · Score: ${Math.round(s.s_final)}`,
action: "MONITOR",
actionCls: "bg-cyan-500/20 text-cyan-400 border-cyan-500/40",
};
}
if (isAlert) {
const pred = s.top_wallets?.[0]?.prediction;
return {
type: "ALERT",
cls: "border-red-500/40 bg-red-500/5",
badgeCls: "bg-red-500/20 text-red-400",
title: `${s.dex?.toUpperCase()} ${s.pool_address?.slice(0,6)}..`,
subtitle: `Score: ${Math.round(s.s_final)} · Rug: ${pred ? Math.round(pred.rug_prob*100) + "%" : "—"} · Dump: ${pred?.dump_window_min ? pred.dump_window_min+"min" : "—"}`,
action: "EXIT NOW",
actionCls: "bg-red-500/20 text-red-400 border-red-500/40",
};
}
if (isWatching) {
return {
type: "WATCH",
cls: "border-yellow-500/40 bg-yellow-500/5",
badgeCls: "bg-yellow-500/20 text-yellow-400",
title: `${s.dex?.toUpperCase()} ${s.pool_address?.slice(0,6)}..`,
subtitle: `Score: ${Math.round(s.s_final)} · Elevated activity`,
action: "MONITOR",
actionCls: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
};
}
return {
type: "CLEAR",
cls: "border-green-500/40 bg-green-500/5",
badgeCls: "bg-green-500/20 text-green-400",
title: "All pools",
subtitle: "No anomaly detected",
action: "CLEAR TO TRADE",
actionCls: "bg-green-500/20 text-green-400 border-green-500/40",
};
}

export default function Panel2LiveFeed() {
const [signals, setSignals] = useState<Signal[]>([]);
const alertCount = signals.filter(s => s.alert_level === "alert" || s.alert_level === "high_conf").length;

useEffect(() => {
supabase
.from("signal_log")
.select("*")
.order("created_at", { ascending: false })
.limit(10)
.then(({ data }) => { if (data) setSignals(data); });

const channel = supabase
.channel("panel2-feed")
.on("postgres_changes", { event: "INSERT", schema: "public", table: "signal_log" },
(payload) => setSignals((prev) => [payload.new as Signal, ...prev].slice(0, 10))
)
.subscribe();

return () => { supabase.removeChannel(channel); };
}, []);
return (
<div className="panel h-full">
<div className="flex items-center justify-between mb-3">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Live Detection Feed</h2>
{alertCount > 0 && (
<span className="text-[10px] bg-red-500 text-white px-2 py-0.5 rounded-full font-bold">
{alertCount} ALERTS
</span>
)}
</div>

<div className="space-y-2 overflow-y-auto max-h-72">
{signals.length === 0 && (
<div className="text-xs text-slate-500 text-center py-8">Monitoring...</div>
)}
{signals.map((s) => {
const entry = feedEntry(s);
return (
<div key={s.id} className={`p-2.5 rounded border ${entry.cls} flex items-start justify-between gap-2`}>
<div className="flex-1 min-w-0">
<div className="flex items-center gap-2 mb-1">
<span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${entry.badgeCls}`}>{entry.type}</span>
<span className="text-xs text-white font-medium truncate">{entry.title}</span>
</div>
<p className="text-[11px] text-slate-400">{entry.subtitle}</p>
</div>
<button className={`text-[10px] px-2 py-1 rounded border font-bold whitespace-nowrap ${entry.actionCls}`}>
{entry.action}
</button>
</div>
);
})}
</div>
</div>
);
}
