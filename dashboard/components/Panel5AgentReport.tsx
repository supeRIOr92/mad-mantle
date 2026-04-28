"use client";
import { useEffect, useState } from "react";
import { supabase, type Wallet } from "@/lib/supabase";

export default function Panel5AgentReport() {
const [wallet, setWallet] = useState<Wallet | null>(null);

useEffect(() => {
// Show highest-risk wallet by default
supabase
.from("wallet_profile")
.select("*")
.eq("agent_type", "MANIPULATOR")
.order("wash_ratio", { ascending: false })
.limit(1)
.then(({ data }) => { if (data?.[0]) setWallet(data[0] as Wallet); });

const channel = supabase
.channel("panel5-agent")
.on("postgres_changes", { event: "*", schema: "public", table: "wallet_profile" },
({ new: w }) => {
if ((w as Wallet).agent_type === "MANIPULATOR") setWallet(w as Wallet);
}
)
.subscribe();

return () => { supabase.removeChannel(channel); };
}, []);

const washPct = wallet ? Math.min((wallet.wash_ratio / 50) * 100, 100) : 0;
return (
<div className="panel h-full">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-3">Agent Report</h2>

{!wallet ? (
<div className="text-xs text-slate-500 text-center py-8">No agents detected yet</div>
) : (
<div className="space-y-2 text-[11px]">
{[
["Type", <span className="text-red-400 font-bold">{wallet.agent_type}</span>],
["ERC-8004", wallet.agent_token_id ? `Token #${wallet.agent_token_id} · Rep ${wallet.reputation_score}/100` : "Unregistered"],
["Wash Ratio", `${wallet.wash_ratio?.toFixed(1)}× (threshold >10×)`],
["Wash Label", wallet.wash_label],
["ROI 7d", wallet.roi_7d != null ? `+${wallet.roi_7d.toFixed(1)}% — ARTIFICIAL` : "—"],
["Vol", `$${((wallet.total_volume_usd||0)/1000).toFixed(0)}K`],
["Verdict", <span className="text-red-400 font-bold">AVOID — active manipulator</span>],
].map(([label, val]) => (
<div key={label as string} className="flex justify-between border-b border-mad-border/50 pb-1">
<span className="text-slate-500">{label}</span>
<span className="text-right text-white">{val}</span>
</div>
))}

<div>
<div className="flex justify-between mb-1">
<span className="text-slate-500">Wash-Like</span>
<span className="text-red-400">{washPct.toFixed(0)}%</span>
</div>
<div className="score-bar-bg">
<div className="h-full bg-red-500 transition-all duration-500" style={{ width: `${washPct}%` }} />
</div>
</div>
</div>
)}
</div>
);
}
