"use client";
import { usePoolScans } from "@/lib/hooks/usePoolScans";

function shortAddr(addr: string) {
return addr.length > 10 ? addr.slice(0, 6) + ".." + addr.slice(-4) : addr;
}

function timeAgo(iso: string) {
const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
if (sec < 60) return `${sec}s ago`;
if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
return `${Math.floor(sec / 3600)}h ago`;
}

function scoreColor(score: number) {
if (score >= 71) return "text-red-400";
if (score >= 41) return "text-yellow-400";
return "text-green-400";
}

function scoreBadge(level: string) {
if (level === "alert" || level === "high_conf")
return { label: "ALERT", cls: "bg-red-500/20 text-red-400 border-red-500/40" };
if (level === "watching")
return { label: "WATCH", cls: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40" };
return { label: "SCAN", cls: "bg-slate-700/40 text-slate-400 border-slate-600" };
}

export default function Panel2LiveFeed() {
const { scans } = usePoolScans(15);

const alertCount = scans.filter(
(s) => s.alert_level === "alert" || s.alert_level === "high_conf"
).length;

return (
<div className="panel h-full">
<div className="flex items-center justify-between mb-3">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">
Live Detection Feed
</h2>
<div className="flex items-center gap-2">
{alertCount > 0 ? (
<span className="text-[10px] bg-red-500 text-white px-2 py-0.5 rounded-full font-bold">
{alertCount} ALERTS
</span>
) : (
<span className="text-[10px] text-slate-600 flex items-center gap-1">
<span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
Scanning...
</span>
)}
</div>
</div>

<div className="space-y-1.5 overflow-y-auto max-h-72">
{scans.length === 0 ? (
<div className="text-[11px] text-slate-500 text-center py-8">
<div className="mb-2">🔍</div>
Scanning 3 DEXes — no events yet
</div>
) : (
scans.map((s) => {
const badge = scoreBadge(s.alert_level);
const topWallet = s.top_wallets?.[0];
return (
<div
key={s.id}
className={`flex items-center gap-2 px-2 py-1.5 rounded text-[11px] transition-colors ${
s.alert_level === "alert" || s.alert_level === "high_conf"
? "bg-red-500/5 border border-red-500/20"
: s.alert_level === "watching"
? "bg-yellow-500/5 border border-yellow-500/10"
: "hover:bg-slate-900/50"
}`}
>
{/* Badge */}
<span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold shrink-0 ${badge.cls}`}>
{badge.label}
</span>

{/* Pool + DEX */}
<div className="flex-1 min-w-0">
<span className="text-white font-mono">{shortAddr(s.pool_address)}</span>
<span className="text-slate-600 ml-1">{s.dex?.toUpperCase()}</span>
{topWallet?.agent_type === "MANIPULATOR" && (
<span className="text-red-400 ml-1 text-[9px]">⚠ suspect wallet</span>
)}
</div>

{/* Score */}
<span className={`font-bold shrink-0 ${scoreColor(s.s_final)}`}>
{Math.round(s.s_final)}
</span>

{/* Time */}
<span className="text-slate-600 shrink-0 text-[9px]">
{timeAgo(s.created_at)}
</span>
</div>
);
})
)}
</div>

<p className="text-[10px] text-slate-600 mt-2">
{scans.length > 0
? `${scans.length} events · polling every 5s`
: "Waiting for first scan cycle..."}
</p>
</div>
);
}
