"use client";
import { useAlerts } from "@/lib/hooks/useAlerts";

function shortAddr(addr: string) {
return addr.length > 10 ? addr.slice(0, 6) + ".." + addr.slice(-4) : addr;
}

function timeAgo(iso: string) {
const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
if (sec < 60) return `${sec}s ago`;
if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
return `${Math.floor(sec / 3600)}h ago`;
}

export default function PanelSignals() {
const { signals } = useAlerts();
return (
<div className={`panel h-full ${signals.length > 0 ? "border-yellow-500/30" : ""}`}>
<div className="flex items-center justify-between mb-3">
<div className="text-xs font-bold text-yellow-400 uppercase tracking-widest">
⚠️ Watching Signals
</div>
<div className="flex items-center gap-2">
<span className="text-[10px] text-slate-500">score &gt; 41</span>
{signals.length > 0 && (
<span className="text-[10px] bg-yellow-500/80 text-black px-2 py-0.5 rounded-full font-bold">
{signals.length}
</span>
)}
</div>
</div>

{signals.length === 0 ? (
<div className="flex flex-col items-center justify-center py-6 text-center">
<span className="text-2xl mb-2">✅</span>
<p className="text-[11px] text-slate-400 font-medium">No signals detected</p>
<p className="text-[10px] text-slate-600 mt-1">Below watching threshold on all pools</p>
</div>
) : (
<div className="space-y-2 overflow-y-auto max-h-48">
{signals.map((s) => (
<div key={s.id} className="p-2.5 rounded border border-yellow-500/20 bg-yellow-500/5">
<div className="flex items-center justify-between mb-1">
<div className="flex items-center gap-2">
<span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded font-bold">
WATCH
</span>
<span className="text-xs text-white font-mono">{shortAddr(s.pool_address)}</span>
<span className="text-[10px] text-slate-500">{s.dex?.toUpperCase()}</span>
</div>
<span className="text-yellow-400 font-bold text-sm">{Math.round(s.s_final)}</span>
</div>
<div className="text-[10px] text-slate-400 flex gap-3">
<span>L1: {Math.round(s.l1_score)}</span>
<span>L2: {Math.round(s.l2_score)}</span>
<span>L3: {Math.round(s.l3_score)}</span>
<span className="ml-auto">{timeAgo(s.created_at)}</span>
</div>
</div>
))}
</div>
)}
</div>
);
}
