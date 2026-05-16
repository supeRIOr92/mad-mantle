"use client";
import { useAppState } from "@/lib/app-state";
import { useWalletProfiles } from "@/lib/hooks/useWalletProfiles";

function riskBar(value: number, max: number) {
const pct = Math.min((value / max) * 100, 100);
const color = pct >= 70 ? "bg-red-500" : pct >= 40 ? "bg-yellow-500" : "bg-green-500";
return { pct, color };
}

export default function Panel5AgentReport() {
const { mode } = useAppState();
const { manipulators, wallets } = useWalletProfiles(10);

// Priority: MANIPULATOR, if empty taking highest wash_ratio wallet
const wallet = manipulators[0] || wallets.slice().sort((a, b) => (b.wash_ratio || 0) - (a.wash_ratio || 0))[0] || null;

const washBar = riskBar(wallet?.wash_ratio || 0, 50);

return (
<div className="panel h-full">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-3">
Agent Report
{wallet?.is_simulated && (
<span className="text-amber-400 text-[10px] ml-2 font-normal">[SIM]</span>
)}
</h2>

{!wallet ? (
<div className="flex flex-col items-center justify-center py-6 text-center">
<span className="text-2xl mb-2">🟢</span>
<p className="text-[11px] text-slate-400 font-medium">No suspicious agents detected</p>
<p className="text-[10px] text-slate-600 mt-1">
Wallet activity within normal patterns
</p>
<div className="mt-3 space-y-1 text-[10px] text-slate-600 text-left">
<div>✔ No wash trading detected</div>
<div>✔ No flash loan abuse</div>
<div>✔ No cycle patterns</div>
</div>
</div>
) : (
<div className="space-y-2 text-[11px]">
{[
["Address", <a href={`https://mantlescan.xyz/address/${wallet.address}`} target="_blank" rel="noopener noreferrer" className="font-mono text-white hover:text-cyan-400 transition-colors">{wallet.address.slice(0, 6)}..{wallet.address.slice(-4)}</a>],
["Type", <span className={wallet.agent_type === "MANIPULATOR" ? "text-red-400 font-bold" : "text-cyan-400"}>{wallet.agent_type}</span>],
["ERC-8004", wallet.agent_token_id ? `Token #${wallet.agent_token_id} · Rep ${wallet.reputation_score}/100` : "Unregistered"],
["Archetype", <span className="text-slate-300">{wallet.archetype || "UNKNOWN"}</span>],
["Wash Ratio", `${wallet.wash_ratio?.toFixed(1)}× (threshold >10×)`],
["Wash Label", wallet.wash_label || "MONITORING"],
["ROI 7d", wallet.roi_7d != null ? (
<span className={wallet.agent_type === "MANIPULATOR" ? "text-red-400" : "text-green-400"}>
+{wallet.roi_7d.toFixed(1)}%{wallet.agent_type === "MANIPULATOR" ? " — ARTIFICIAL" : ""}
</span>
) : "—"],
["Volume", `$${((wallet.total_volume_usd || 0) / 1000).toFixed(0)}K`],
...(wallet.is_simulated ? [["Simulated", <span className="text-amber-400">Yes — SIMULATED DATA</span>]] : []),
["Verdict", wallet.agent_type === "MANIPULATOR"
? <span className="text-red-400 font-bold">AVOID — active manipulator</span>
: <span className="text-yellow-400">MONITOR — elevated activity</span>
],
].map(([label, val]) => (
<div key={label as string} className="flex justify-between border-b border-mad-border/50 pb-1">
<span className="text-slate-500">{label}</span>
<span className="text-right text-white">{val}</span>
</div>
))}

{/* Wash bar */}
<div className="pt-1">
<div className="flex justify-between mb-1">
<span className="text-slate-500">Wash-Like Activity</span>
<span className={washBar.pct >= 70 ? "text-red-400" : "text-slate-400"}>
{washBar.pct.toFixed(0)}%
</span>
</div>
<div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
<div
className={`h-full ${washBar.color} transition-all duration-500`}
style={{ width: `${washBar.pct}%` }}
/>
</div>
</div>
</div>
)}
</div>
);
}
