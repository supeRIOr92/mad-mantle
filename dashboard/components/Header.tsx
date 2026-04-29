"use client";
import { useEffect, useState } from "react";
import { useAppState } from "@/lib/app-state";

export default function Header() {
const [time, setTime] = useState("");
const { mode, setMode, view, setView } = useAppState();

useEffect(() => {
const update = () => {
setTime(new Date().toUTCString().split(" ")[4] + " UTC");
};
update();
const t = setInterval(update, 1000);
return () => clearInterval(t);
}, []);
return (
<div className={`border-b border-mad-border transition-colors ${mode === "demo" ? "bg-amber-950/20" : "bg-mad-panel"}`}>
{/* Top Bar — Mode Switch */}
<div className="flex items-center justify-between px-6 py-2.5">
<div className="flex items-center gap-4">
<span className="text-lg font-bold text-white tracking-tight">MAD</span>
<span className="text-xs text-slate-400">— Mantle Anomaly Detector</span>
{mode === "demo" && (
<span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/40 px-2 py-0.5 rounded font-bold">
DEMO MODE
</span>
)}
</div>

<div className="flex items-center gap-3">
{/* Mode Toggle */}
<div className="flex items-center gap-1">
<button
onClick={() => setMode("live")}
className={`text-[10px] px-2.5 py-1 rounded font-bold border transition-all ${
mode === "live"
? "bg-green-500/20 text-green-400 border-green-500/40"
: "bg-transparent text-slate-500 border-slate-700 hover:border-slate-500"
}`}
>
LIVE
</button>
<button
onClick={() => setMode("demo")}
className={`text-[10px] px-2.5 py-1 rounded font-bold border transition-all ${
mode === "demo"
? "bg-amber-500/20 text-amber-400 border-amber-500/40"
: "bg-transparent text-slate-500 border-slate-700 hover:border-slate-500"
}`}
>
DEMO
</button>
</div>

<div className="flex items-center gap-2 text-xs ml-2">
<span className={`w-2 h-2 rounded-full inline-block ${mode === "demo" ? "bg-amber-400" : "bg-green-500 pulse-red"}`} />
<span className={mode === "demo" ? "text-amber-400 font-semibold" : "text-green-400 font-semibold"}>
{mode === "demo" ? "DEMO" : "LIVE"}
</span>
<span className="text-slate-400 ml-1">{time}</span>
</div>
</div>
</div>

{/* Second Bar — View Switch */}
<div className="flex items-center gap-1 px-6 pb-2">
<button
onClick={() => setView("activity")}
className={`text-[10px] px-3 py-1 rounded font-bold border transition-all ${
view === "activity"
? "bg-slate-600/40 text-slate-200 border-slate-500"
: "bg-transparent text-slate-500 border-slate-700 hover:border-slate-500 hover:text-slate-300"
}`}
>
Activity View
</button>
<button
onClick={() => setView("risk")}
className={`text-[10px] px-3 py-1 rounded font-bold border transition-all ${
view === "risk"
? "bg-red-500/20 text-red-400 border-red-500/40"
: "bg-transparent text-slate-500 border-slate-700 hover:border-slate-500 hover:text-slate-300"
}`}
>
Risk View
</button>
<span className="text-slate-700 text-xs ml-2">|</span>
<span className="text-[10px] text-slate-600 ml-2">
{view === "activity" ? "Ecosystem monitoring" : "Anomaly & decision layer"}
</span>
</div>
</div>
);
}
