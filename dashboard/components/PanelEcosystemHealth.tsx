"use client";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { usePoolScans } from "@/lib/hooks/usePoolScans";

export default function PanelEcosystemHealth() {
const { scans, totalCount, avgScore, scoreTimeline, topRisk } = usePoolScans(48);

const activePoolCount = new Set(scans.map((s) => s.pool_address)).size;

const healthLabel =
avgScore >= 71 ? "CRITICAL" :
avgScore >= 41 ? "ELEVATED" :
avgScore >= 20 ? "NORMAL" : "CLEAN";

const healthColor =
avgScore >= 71 ? "text-red-400" :
avgScore >= 41 ? "text-yellow-400" :
"text-green-400";

// Score distribution
const dist = { clean: 0,normal: 0,elevated: 0, critical: 0 };
scans.forEach((s) => {
if (s.s_final >= 71) dist.critical++;
else if (s.s_final >= 41) dist.elevated++;
else if (s.s_final >= 20) dist.normal++;
else dist.clean++;
});
const total = scans.length || 1;
return (
<div className="panel h-full">
<div className="flex items-center justify-between mb-3">
<div className="text-xs font-bold text-slate-300 uppercase tracking-widest">
Ecosystem Health
</div>
<span className={`text-[10px] font-bold ${healthColor}`}>{healthLabel}</span>
</div>

{/* Top metrics */}
<div className="flex gap-6 mb-3">
<div>
<div className={`text-2xl font-bold ${healthColor}`}>{avgScore}</div>
<div className="text-[10px] text-slate-500">Avg Score</div>
</div>
<div>
<div className="text-2xl font-bold text-white">{activePoolCount}</div>
<div className="text-[10px] text-slate-500">Active Pools</div>
</div>
<div>
<div className="text-2xl font-bold text-white">{totalCount}</div>
<div className="text-[10px] text-slate-500">Total Scans</div>
</div>
</div>

{/* Mini chart */}
{scoreTimeline.length > 1 ? (
<ResponsiveContainer width="100%" height={70}>
<AreaChart data={scoreTimeline} margin={{ top: 0, right: 0, left: -30, bottom: 0 }}>
<XAxis dataKey="time" hide />
<YAxis domain={[0, 100]} hide />
<Tooltip
contentStyle={{ background: "#0f0f1a", border: "1px solid #1a1a2e", fontSize: 10 }}
formatter={(v: any) => [`${v}`, "Score"]}
/>
<Area
dataKey="score"
stroke={avgScore >= 71 ? "#ef4444" : avgScore >= 41 ? "#eab308" : "#22c55e"}
fill={avgScore >= 71 ? "#ef444420" : avgScore >= 41 ? "#eab30820" : "#22c55e20"}
strokeWidth={2}
dot={false}
/>
</AreaChart>
</ResponsiveContainer>
) : (
<div className="h-[70px] flex items-center justify-center text-[11px] text-slate-600">
Accumulating baseline data...
</div>
)}

{/* Score distribution */}
{scans.length > 0 && (
<div className="mt-3">
<div className="flex gap-1 h-1.5 rounded-full overflow-hidden">
<div className="bg-green-500" style={{ width: `${(dist.clean / total) * 100}%` }} />
<div className="bg-slate-400" style={{ width: `${(dist.normal / total) * 100}%` }} />
<div className="bg-yellow-500" style={{ width: `${(dist.elevated / total) * 100}%` }} />
<div className="bg-red-500" style={{ width: `${(dist.critical / total) * 100}%` }} />
</div>
<div className="flex gap-3 mt-1 text-[9px] text-slate-600">
<span className="text-green-500">Clean {dist.clean}</span>
<span className="text-slate-400">Normal {dist.normal}</span>
<span className="text-yellow-500">Elevated {dist.elevated}</span>
<span className="text-red-500">Critical {dist.critical}</span>
</div>
</div>
)}
</div>
);
}
