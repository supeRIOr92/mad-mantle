"use client";
import { useEffect, useState } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { supabase, type Wallet } from "@/lib/supabase";

function bubbleColor(type: string) {
if (type === "CONFIRMED AGENT" || type === "SMART MONEY") return "#22c55e";
if (type === "PROBABLE AGENT") return "#eab308";
if (type === "MANIPULATOR") return "#ef4444";
return "#64748b";
}

export default function Panel6BubbleChart() {
const [wallets, setWallets] = useState<Wallet[]>([]);

useEffect(() => {
const fetch = () => {
supabase
.from("wallet_profile")
.select("*")
.not("roi_7d", "is", null)
.limit(30)
.then(({ data }) => { if (data) setWallets(data as Wallet[]); });
};
fetch();

const channel = supabase
.channel("panel6-bubble")
.on("postgres_changes", { event: "*", schema: "public", table: "wallet_profile" },
() => fetch()
)
.subscribe();

return () => { supabase.removeChannel(channel); };
}, []);

const data = wallets.map(w => ({
x: Math.round((w.total_volume_usd || 0) / 1000),
y: Math.round(w.roi_7d || 0),
z: Math.max((w.tx_count || 1) * 3, 8),
label: w.address.slice(0, 6) + "..",
type: w.agent_type,
}));
return (
<div className="panel h-full">
<div className="flex items-center justify-between mb-3">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Agent Bubble Chart</h2>
<div className="flex gap-3 text-[10px]">
{[["#22c55e","Smart / Confirmed"],["#eab308","Probable"],["#ef4444","Manipulator"],["#64748b","Unknown"]].map(([c,l]) => (
<span key={l} className="flex items-center gap-1">
<span className="w-2 h-2 rounded-full inline-block" style={{ background: c }} />{l}
</span>
))}
</div>
</div>

{data.length === 0 ? (
<div className="text-xs text-slate-500 text-center py-8">No wallet data yet</div>
) : (
<ResponsiveContainer width="100%" height={200}>
<ScatterChart margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
<XAxis dataKey="x" name="Volume 24h ($K)" tick={{ fontSize: 10, fill: "#64748b" }} label={{ value: "Vol ($K)", position: "insideBottom", offset: -2, fontSize: 10, fill: "#64748b" }} />
<YAxis dataKey="y" name="ROI 7d (%)" tick={{ fontSize: 10, fill: "#64748b" }} label={{ value: "ROI 7d (%)", angle: -90, position: "insideLeft", fontSize: 10, fill: "#64748b" }} />
<Tooltip
cursor={{ strokeDasharray: "3 3" }}
contentStyle={{ background: "#0f0f1a", border: "1px solid #1a1a2e", fontSize: 11 }}
formatter={(val, name) => [val, name]}
/>
<Scatter data={data} shape={(props: any) => {
const { cx, cy, payload } = props;
const r = Math.sqrt(payload.z) * 2;
return (
<g>
<circle cx={cx} cy={cy} r={r} fill={bubbleColor(payload.type)} fillOpacity={0.7} stroke={bubbleColor(payload.type)} strokeWidth={1} />
<text x={cx} y={cy - r - 3} textAnchor="middle" fontSize={9} fill="#94a3b8">{payload.label}</text>
</g>
);
}}>
{data.map((_, i) => <Cell key={i} fill={bubbleColor(_.type)} />)}
</Scatter>
</ScatterChart>
</ResponsiveContainer>
)}
</div>
);
}
