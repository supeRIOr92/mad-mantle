"use client";
import { useEffect, useState } from "react";
import { supabase, type Signal } from "@/lib/supabase";
import { useAppState } from "@/lib/app-state";

function scoreColor(level: string) {
if (level === "high_conf" || level === "alert") return "text-red-400";
if (level === "watching") return "text-yellow-400";
return "text-green-400";
}

function scoreBadge(level: string) {
if (level === "high_conf") return { label: "ALERT", cls: "bg-red-500/20 text-red-400 border-red-500/40" };
if (level === "alert") return { label: "ALERT", cls: "bg-red-500/20 text-red-400 border-red-500/40" };
if (level === "watching") return { label: "WATCH", cls: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40" };
return { label: "CLEAR", cls: "bg-green-500/20 text-green-400 border-green-500/40" };
}

function barColor(level: string) {
if (level === "high_conf" || level === "alert") return "bg-red-500";
if (level === "watching") return "bg-yellow-500";
return "bg-green-500";
}

function shortPool(addr: string) {
return addr.length > 12 ? addr.slice(0, 6) + ".." + addr.slice(-4) : addr;
}

export default function Panel1LiveScores() {
const [signals, setSignals] = useState <Signal[]>([]);
const { mode } = useAppState();

useEffect(() => {
// Initial fetch — latest per pool
supabase
.from("signal_log")
.select("*")
.order("created_at", { ascending: false })
.eq("environment", mode)
.limit(20)
.then(({ data }) => {
if (!data) return;
// Dedupe by pool_address — keep latest
const seen = new Set<string>();
const deduped = data.filter((s) => {
if (seen.has(s.pool_address)) return false;
seen.add(s.pool_address);
return true;
});
setSignals(deduped.slice(0, 8));
});

// Realtime subscription
const channel = supabase
.channel("panel1-scores")
.on("postgres_changes", { event: "INSERT", schema: "public", table: "signal_log" },
(payload) => {
setSignals((prev) => {
const updated = [payload.new as Signal, ...prev.filter(s => s.pool_address !== payload.new.pool_address)];
return updated.slice(0, 8);
});
}
)
.subscribe();

return () => { supabase.removeChannel(channel); };
}, [mode]);
return (
<div className="panel h-full">
<div className="flex items-center justify-between mb-3">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Live DEX Anomaly Scores</h2>
</div>

<div className="space-y-2">
{signals.length === 0 && (
<div className="text-xs text-slate-500 text-center py-8">Waiting for signals...</div>
)}
{signals.map((s) => {
const badge = scoreBadge(s.alert_level);
return (
<div key={s.id} className="flex items-center gap-3 p-2 rounded bg-mad-bg hover:bg-slate-900 cursor-pointer transition-colors">
<div className="flex-1 min-w-0">
<div className="flex items-center gap-2 mb-1">
<a
href={`https://mantlescan.xyz/address/${s.pool_address}`}
target="_blank" rel="noopener noreferrer" className="text-xs text-white font-medium truncate hover:text-cyan-400 transition-colors">
{shortPool(s.pool_address)} </a>
<span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold ${badge.cls}`}>{badge.label}</span>
<span className="text-xs text-slate-400 ml-auto">{s.dex?.toUpperCase()}</span>
</div>
<div className="score-bar-bg">
<div className={`h-full ${barColor(s.alert_level)} transition-all duration-500`}
style={{ width: `${Math.min(s.s_final, 100)}%` }} />
</div>
</div>
<span className={`text-sm font-bold w-8 text-right ${scoreColor(s.alert_level)}`}>
{Math.round(s.s_final)}
</span>
</div>
);
})}
</div>
<p className="text-[10px] text-slate-600 mt-3">Click any pool for L1/L2/L3 breakdown + prediction</p>
</div>
);
}
