"use client";
import { usePoolScans } from "@/lib/hooks/usePoolScans";
import { useAlerts } from "@/lib/hooks/useAlerts";

export default function PanelModelStatus() {
const { scans, totalCount } = usePoolScans(200);
const { alerts, signals } = useAlerts();

const sampleSize = scans.length;
const isWarming = sampleSize < 10;

const withL1 = scans.filter((s) => s.l1_score > 0).length;
const withL2 = scans.filter((s) => s.l2_score > 0).length;
const withL3 = scans.filter((s) => s.l3_score > 0).length;

const precision = sampleSize > 0
? Math.round(((alerts.length + signals.length) / sampleSize) * 100)
: 0;

const l1pct = sampleSize > 0 ? Math.round((withL1 / sampleSize) * 100) : 0;
const l2pct = sampleSize > 0 ? Math.round((withL2 / sampleSize) * 100) : 0;
const l3pct = sampleSize > 0 ? Math.round((withL3 / sampleSize) * 100) : 0;
return (
<div className="panel h-full">
<div className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-3">
Model Status
</div>

<div className="flex items-center gap-2 mb-3">
<span className={`text-sm font-bold ${isWarming ? "text-amber-400" : "text-green-400"}`}>
{isWarming ? "Warming Up" : "Active"}
</span>
<span className="text-[10px] text-slate-600">
{sampleSize} sample{sampleSize !== 1 ? "s" : ""}
</span>
</div>

{isWarming ? (
<p className="text-[11px] text-slate-500 mb-3">
Accuracy will stabilize after data accumulation
</p>
) : (
<div className="flex gap-4 mb-3">
<div>
<div className="text-xl font-bold text-green-400">{precision}%</div>
<div className="text-[10px] text-slate-500">Signal Rate</div>
</div>
<div>
<div className="text-xl font-bold text-white">{totalCount}</div>
<div className="text-[10px] text-slate-500">30d samples</div>
</div>
</div>
)}

{/* Layer status */}
<div className="space-y-1.5 text-[11px]">
{[
{ label: "L1 Z-score", pct: l1pct },
{ label: "L2 Wash", pct: l2pct },
{ label: "L3 Cycle", pct: l3pct },
{ label: "Predictor", pct: sampleSize > 0 ? 100 : 0 },
].map(({ label, pct }) => (
<div key={label} className="flex items-center gap-2">
<span className={pct > 0 ? "text-green-400" : "text-slate-600"}>✔</span>
<span className="text-slate-400 w-20">{label}</span>
<div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
<div
className="h-full bg-green-500/60 transition-all duration-700"
style={{ width: `${pct}%` }}
/>
</div>
<span className="text-slate-600 text-[10px] w-8 text-right">{pct}%</span>
</div>
))}
</div>
</div>
);
}
