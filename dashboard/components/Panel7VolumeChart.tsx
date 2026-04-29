"use client";
import { useEffect, useState } from "react";
import { AreaChart, Area, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ComposedChart } from "recharts";
import { supabase, type Signal } from "@/lib/supabase";
import { useAppState } from "@/lib/app-state";

function bollinger(data: number[], period = 20, sigma = 2) {
return data.map((_, i) => {
const slice = data.slice(Math.max(0, i - period + 1), i + 1);
const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
const std = Math.sqrt(slice.reduce((a, b) => a + (b - mean) ** 2, 0) / slice.length);
return { sma: mean, upper: mean + sigma * std, lower: mean - sigma * std };
});
}

export default function Panel7VolumeChart() {
const [signals, setSignals] = useState<Signal[]>([]);
const { mode } = useAppState();

useEffect(() => {
supabase
.from("signal_log")
.select("created_at,volume_usd,s_final,alert_level,pool_address,dex")
.eq("environment", mode)
.order("created_at", { ascending: true })
.limit(48)
.then(({ data }) => { if (data) setSignals(data as Signal[]); });

const channel = supabase
.channel("panel7-volume")
.on("postgres_changes", { event: "INSERT", schema: "public", table: "signal_log" },
(payload) => setSignals(prev => [...prev.slice(-47), payload.new as Signal])
)
.subscribe();

return () => { supabase.removeChannel(channel); };
}, [mode]);

const vols = signals.map(s => (s.volume_usd || 0) / 1000);
const bands = bollinger(vols);

const chartData = signals.map((s, i) => ({
time: new Date(s.created_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
volume: Math.round(vols[i] * 10) / 10,
upper: Math.round(bands[i].upper * 10) / 10,
lower: Math.round(bands[i].lower * 10) / 10,
sma: Math.round(bands[i].sma * 10) / 10,
alert: s.alert_level === "alert" || s.alert_level === "high_conf" ? vols[i] : null,
}));

const topPool = signals[signals.length - 1];
return (
<div className="panel h-full">
<div className="flex items-center justify-between mb-3">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">
{topPool ? `${topPool.dex?.toUpperCase()} ${topPool.pool_address?.slice(0,6)}.. · 24h` : "Volume Chart · 24h"}
</h2>
<span className="text-[10px] text-slate-500">Bollinger Bands (adaptive σ v2.0)</span>
</div>

<div className="flex gap-4 text-[10px] text-slate-500 mb-2">
<span className="flex items-center gap-1"><span className="w-3 border-t border-dashed border-slate-500 inline-block" /> Upper</span>
<span className="flex items-center gap-1"><span className="w-3 border-t border-dashed border-slate-500 inline-block" /> Lower</span>
<span className="flex items-center gap-1"><span className="w-3 border-t border-slate-400 inline-block" /> SMA(20)</span>
<span className="flex items-center gap-1"><span className="w-3 border-t border-cyan-400 inline-block" /> Volume ($K)</span>
</div>

{chartData.length === 0 ? (
<div className="text-xs text-slate-500 text-center py-8">Collecting data...</div>
) : (
<ResponsiveContainer width="100%" height={200}>
<ComposedChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
<XAxis dataKey="time" tick={{ fontSize: 9, fill: "#64748b" }} interval="preserveStartEnd" />
<YAxis tick={{ fontSize: 9, fill: "#64748b" }} />
<Tooltip
contentStyle={{ background: "#0f0f1a", border: "1px solid #1a1a2e", fontSize: 10 }}
formatter={(val: any, name: string) => [`${val}K`, name]}
/>
<Area dataKey="upper" stroke="#475569" strokeDasharray="3 3" fill="transparent" strokeWidth={1} dot={false} />
<Area dataKey="lower" stroke="#475569" strokeDasharray="3 3" fill="transparent" strokeWidth={1} dot={false} />
<Line dataKey="sma" stroke="#94a3b8" strokeWidth={1} dot={false} />
<Area dataKey="volume" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.15} strokeWidth={2} dot={false} />
<Line dataKey="alert" stroke="#ef4444" strokeWidth={0} dot={{ r: 5, fill: "#ef4444" }} />
</ComposedChart>
</ResponsiveContainer>
)}
</div>
);
}
