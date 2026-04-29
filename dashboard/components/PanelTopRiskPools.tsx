"use client";
import { usePoolScans } from "@/lib/hooks/usePoolScans";

function shortAddr(addr: string) {
return addr.length > 10 ? addr.slice(0, 6) + ".." + addr.slice(-4) : addr;
}

function scoreColor(score: number) {
if (score >= 71) return "text-red-400";
if (score >= 41) return "text-yellow-400";
return "text-green-400";
}

function scoreBg(score: number) {
if (score >= 71) return "bg-red-500";
if (score >= 41) return "bg-yellow-500";
return "bg-green-500";
}

export default function PanelTopRiskPools() {
const { topRisk, scans } = usePoolScans(48);

return (
<div className="panel h-full">
<div className="flex items-center justify-between mb-3">
<div className="text-xs font-bold text-slate-300 uppercase tracking-widest">
Top Risk Pools
</div>
<span className="text-[10px] text-slate-500">{scans.length} scanned</span>
</div>

{topRisk.length === 0 ? (
<div className="text-[11px] text-slate-500 py-4 text-center">
Scanning pools — no elevated risk detected
</div>
) : (
<div className="space-y-2">
{topRisk.map((s, i) => (
<div key={s.id} className="flex items-center gap-2">
<span className="text-slate-600 text-[10px] w-4">{i + 1}</span>
<div className="flex-1 min-w-0">
<div className="flex items-center justify-between mb-0.5">
<span className="text-xs text-white font-mono truncate">
{shortAddr(s.pool_address)}
</span>
<span className="text-[10px] text-slate-500 ml-2">{s.dex?.toUpperCase()}</span>
</div>
<div className="h-1 bg-slate-800 rounded-full overflow-hidden">
<div
className={`h-full ${scoreBg(s.s_final)} transition-all duration-500`}
style={{ width: `${Math.min(s.s_final, 100)}%` }}
/>
</div>
</div>
<span className={`text-sm font-bold w-8 text-right ${scoreColor(s.s_final)}`}>
{Math.round(s.s_final)}
</span>
</div>
))}
</div>
)}

<p className="text-[10px] text-slate-600 mt-3">
Sorted by anomaly score — updated in real-time</p>
</div>
);
}
