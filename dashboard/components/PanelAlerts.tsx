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
}export default function PanelAlerts() {
const { alerts } = useAlerts();

return (
<div className={`panel h-full ${alerts.length > 0 ? "border-red-500/30" : ""}`}>
<div className="flex items-center justify-between mb-3">
<div className="text-xs font-bold text-red-400 uppercase tracking-widest">
🚨 Active Alerts
</div>
<div className="flex items-center gap-2">
<span className="text-[10px] text-slate-500">score &gt; 71</span>
{alerts.length > 0 && (
<span className="text-[10px] bg-red-500 text-white px-2 py-0.5 rounded-full font-bold">
{alerts.length}
</span>
)}
</div>
</div>

{alerts.length === 0 ? (
<div className="flex flex-col items-center justify-center py-6 text-center">
<span className="text-2xl mb-2">🟢</span>
<p className="text-[11px] text-slate-400 font-medium">No active alerts</p>
<p className="text-[10px] text-slate-600 mt-1">System monitoring — all pools within threshold</p>
</div>
) : (
<div className="space-y-2 overflow-y-auto max-h-48">
{alerts.map((s) => {
const topWallet = s.top_wallets?.[0];
const pred = topWallet?.prediction;
return (
<div key={s.id} className="p-2.5 rounded border border-red-500/30 bg-red-500/5">
<div className="flex items-center justify-between mb-1">
<div className="flex items-center gap-2">
<span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-bold">
{s.alert_level === "high_conf" ? "HIGH CONF" : "ALERT"}
</span>
<span className="text-xs text-white font-mono">{shortAddr(s.pool_address)}</span>
<span className="text-[10px] text-slate-500">{s.dex?.toUpperCase()}</span>
</div>
<span className="text-red-400 font-bold text-sm">{Math.round(s.s_final)}</span>
</div>
<div className="text-[10px] text-slate-400 flex gap-3">
<span>Rug: {pred ? `${Math.round(pred.rug_prob * 100)}%` : "—"}</span>
<span>Dump: {pred?.dump_window_min ? `~${pred.dump_window_min}min` : "—"}</span>
<span className="ml-auto">{timeAgo(s.created_at)}</span>
</div>
</div>
);
})}
</div>
)}
</div>
);
}
