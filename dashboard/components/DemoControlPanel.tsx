"use client";
import { useState } from "react";
import { useAppState } from "@/lib/app-state";

const SCENARIOS = ["FLASH_WASH", "PUMP_DUMP", "CLEAN_MARKET", "FALSE_POSITIVE"] as const;
type Scenario = typeof SCENARIOS[number];

const SCENARIO_DESC: Record<Scenario, string> = {
FLASH_WASH: "Wash attack build-up → alert trigger",
PUMP_DUMP: "Volume spike → delayed dump detection",
CLEAN_MARKET: "Stable market — silence is a signal",
FALSE_POSITIVE: "Borderline score — system doesn't over-trigger",
};

const DEMO_API = "http://localhost:8001";
export default function DemoControlPanel() {
const { mode } = useAppState();
const [selected, setSelected] = useState<Scenario>("FLASH_WASH");
const [status, setStatus] = useState<"ready" | "running" | "paused" | "complete">("ready");
const [speed, setSpeed] = useState(1.0);
const [step, setStep] = useState(0);
const [totalSteps, setTotalSteps] = useState(0);

if (mode !== "demo") return null;

const call = async (path: string, body?: object) => {
try {
const res = await fetch(`${DEMO_API}${path}`, {
method: body !== undefined ? "POST" : "GET",
headers: { "Content-Type": "application/json" },
body: body ? JSON.stringify(body) : undefined,
});
return await res.json();
} catch (e) {
console.error("[DemoControlPanel] API error:", e);
return null;
}
};

const handleStart = async () => {
const result = await call("/demo/start", { scenario: selected, speed });
if (result?.ok) {
setStatus("running");
setTotalSteps(result.steps || 0);
setStep(0);
const interval = setInterval(async () => {
const s = await call("/demo/status");
if (s) {
setStep(s.step || 0);
if (!s.running) {
setStatus("complete");
clearInterval(interval);
} else if (s.paused) {
setStatus("paused");
} else {
setStatus("running");
}
}
}, 1000);
}
};

const handlePause = async () => {
const result = await call("/demo/pause", {});
if (result?.ok) {
setStatus(result.state === "paused" ? "paused" : "running");
}
};

const handleReset = async () => {
await call("/demo/reset", {});
setStatus("ready");
setStep(0);
setTotalSteps(0);
};

const statusColor = {
ready: "text-slate-400",
running: "text-green-400",
paused: "text-amber-400",
complete: "text-cyan-400",
}[status];

const statusLabel = {
ready: "Ready",
running: `Running... (${step}/${totalSteps})`,
paused: "Paused",
complete: "Complete ✓",
}[status];
return (
<div className="mx-4 mt-3 p-4 rounded-lg border border-amber-500/30 bg-amber-950/10">
<div className="flex items-center justify-between mb-3">
<h3 className="text-xs font-bold text-amber-400 uppercase tracking-widest">
Demo Control Panel
</h3>
<span className={`text-xs font-semibold ${statusColor}`}>{statusLabel}</span>
</div>

<div className="flex gap-2 flex-wrap mb-3">
{SCENARIOS.map((s) => (
<button
key={s}
onClick={() => setSelected(s)}
disabled={status === "running"}
className={`text-[10px] px-3 py-1.5 rounded border font-bold transition-all disabled:opacity-50 ${
selected === s
? "bg-amber-500/20 text-amber-400 border-amber-500/40"
: "bg-transparent text-slate-500 border-slate-700 hover:border-slate-500 hover:text-slate-300"
}`}
>
{s.replace(/_/g, " ")}
</button>
))}
</div>

<p className="text-[11px] text-slate-500 mb-3 italic">
{SCENARIO_DESC[selected]}
</p>

<div className="flex items-center gap-2 flex-wrap">
<button
onClick={handleStart}
disabled={status === "running"}
className="text-[11px] px-3 py-1.5 rounded border font-bold bg-green-500/20 text-green-400 border-green-500/40 hover:bg-green-500/30 disabled:opacity-40 transition-all"
>
▶ Start
</button>

<button
onClick={handlePause}
disabled={status === "ready" || status === "complete"}
className="text-[11px] px-3 py-1.5 rounded border font-bold bg-amber-500/20 text-amber-400 border-amber-500/40 hover:bg-amber-500/30 disabled:opacity-40 transition-all"
>
{status === "paused" ? "▶ Resume" : "⏸ Pause"}
</button>

<button
onClick={() => setSpeed(speed === 1 ? 2 : speed === 2 ? 5 : 1)}
disabled={status === "running"}
className="text-[11px] px-3 py-1.5 rounded border font-bold bg-slate-700/40 text-slate-300 border-slate-600 hover:border-slate-400 disabled:opacity-40 transition-all"
>
⏩ Speed x{speed}
</button>

<button
onClick={handleReset}
className="text-[11px] px-3 py-1.5 rounded border font-bold bg-slate-700/40 text-slate-400 border-slate-600 hover:border-slate-400 hover:text-slate-300 transition-all"
>
🔄 Reset
</button>

{totalSteps > 0 && (
<div className="flex-1 min-w-24">
<div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
<div
className="h-full bg-amber-400 transition-all duration-500"
style={{ width: `${(step / totalSteps) * 100}%` }}
/>
</div>
</div>
)}
</div>
</div>
);
}
