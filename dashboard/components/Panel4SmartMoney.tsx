"use client";
import { useAppState } from "@/lib/app-state";
import { useWalletProfiles } from "@/lib/hooks/useWalletProfiles";

function agentBadge(type: string) {
if (type === "CONFIRMED AGENT") return "text-green-400";
if (type === "PROBABLE AGENT") return "text-cyan-400";
if (type === "MANIPULATOR") return "text-red-400";
if (type === "SMART MONEY") return "text-purple-400";
return "text-slate-400";
}

function riskTag(wallet: any): string[] {
const tags: string[] = [];
if (wallet.wash_ratio > 10) tags.push("Wash Loop");
if (wallet.aave_modifier >= 1.5) tags.push("Flash Loan");
if (wallet.roi_7d && wallet.roi_7d > 50) tags.push("Early Buyer");
if (wallet.agent_type === "MANIPULATOR") tags.push("Liquidity Drainer");
if (wallet.archetype === "PUMP_DUMP") tags.push("Pump & Dump");
if (wallet.archetype === "COORDINATED_WASH") tags.push("Wash Loop Participant");
return tags.slice(0, 2);
}

function tagColor(tag: string) {
if (tag === "Wash Loop" || tag === "Wash Loop Participant") return "bg-red-500/20 text-red-400 border-red-500/30";
if (tag === "Flash Loan") return "bg-orange-500/20 text-orange-400 border-orange-500/30";
if (tag === "Early Buyer") return "bg-green-500/20 text-green-400 border-green-500/30";
if (tag === "Liquidity Drainer") return "bg-red-500/20 text-red-400 border-red-500/30";
if (tag === "Pump & Dump") return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
return "bg-slate-500/20 text-slate-400 border-slate-500/30";
}

function riskScore(wallet: any): number {
let score = 0;
if (wallet.wash_ratio > 10) score += 40;
else if (wallet.wash_ratio > 5) score += 20;
if (wallet.aave_modifier >= 1.5) score += 30;
else if (wallet.aave_modifier >= 1.2) score += 15;
if (wallet.agent_type === "MANIPULATOR") score += 30;
return Math.min(score, 100);
}

export default function Panel4SmartMoney() {
const { mode, view } = useAppState();
const { wallets, manipulators, smartMoney } = useWalletProfiles(10);

const isRiskView = view === "risk";
const displayWallets = isRiskView
? [...manipulators, ...smartMoney].slice(0, 7)
: smartMoney.slice(0, 5);
return (
<div className="panel h-full">
<div className="mb-2">
<h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest">
{isRiskView ? "Wallet Risk Analysis" : "Smart Money Leaderboard"}
{mode === "demo" && (
<span className="text-amber-400 text-[10px] ml-2 font-normal">⚠️ DEMO</span>
)}
</h2>
<p className="text-[10px] text-slate-500 mt-0.5">
{isRiskView
? "Ranked by risk score — suspicious actors highlighted"
: "7d rolling — smart_score = (1+ROI) × (1–wash_penalty) × rep/100"}
</p>
</div>

{wallets.length === 0 ? (
<div className="text-[11px] text-slate-500 text-center py-6">
Wallet activity within normal patterns
</div>
) : (
<div className="space-y-2 overflow-y-auto max-h-64">
{displayWallets.map((w, i) => {
const tags = riskTag(w);
const risk = riskScore(w);
const isManipulator = w.agent_type === "MANIPULATOR";

return (
<div
key={w.address}
className={`p-2 rounded border transition-colors ${
isManipulator
? "bg-red-500/5 border-red-500/20"
: "bg-mad-bg border-mad-border/50"
}`}
>
<div className="flex items-center gap-2 mb-1">
<span className="text-slate-600 text-[10px] w-4">{i + 1}</span>
<span className="text-xs text-white font-mono">
{w.address.slice(0, 6)}..{w.address.slice(-4)}
</span>
{w.is_simulated && (
<span className="text-[9px] text-amber-400 border border-amber-500/40 px-1 rounded">SIM</span>
)}
<span className={`text-[10px] font-semibold ml-auto ${agentBadge(w.agent_type)}`}>
{w.agent_type}
</span>
</div>

{/* Tags */}
{tags.length > 0 && (
<div className="flex gap-1 mb-1 ml-6">
{tags.map((tag) => (
<span key={tag} className={`text-[9px] px-1.5 py-0.5 rounded border font-medium ${tagColor(tag)}`}>
{tag}
</span>
))}
</div>
)}

<div className="flex items-center gap-3 ml-6 text-[10px] text-slate-500">
{isRiskView ? (
<>
{/* Risk score bar */}
<div className="flex items-center gap-1 flex-1">
<span className="text-slate-600">Risk</span>
<div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
<div
className={`h-full transition-all duration-500 ${
risk >= 70 ? "bg-red-500" : risk >= 40 ? "bg-yellow-500" : "bg-green-500"
}`}
style={{ width: `${risk}%` }}
/>
</div>
<span className={risk >= 70 ? "text-red-400" : risk >= 40 ? "text-yellow-400" : "text-green-400"}>
{risk}
</span>
</div>
<span>Wash {w.wash_ratio?.toFixed(1)}×</span>
</>
) : (
<>
<span className="text-purple-400">
Score {(w.smart_score || 0).toFixed(3)}
</span>
<span className="text-green-400">
{w.roi_7d != null ? `+${w.roi_7d.toFixed(1)}%` : "—"}
</span>
<span>Wash {w.wash_ratio?.toFixed(1)}×</span>
<span className="ml-auto">
${((w.total_volume_usd || 0) / 1000).toFixed(0)}K
</span>
</>
)}
</div>
</div>
);
})}
</div>
)}

{manipulators.length > 0 && isRiskView && (
<p className="text-[10px] text-red-500/70 mt-2">
⛔ {manipulators.length} active manipulator{manipulators.length > 1 ? "s" : ""} detected
</p>
)}
</div>
);
}
