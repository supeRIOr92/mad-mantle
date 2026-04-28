"use client";
import { useEffect, useState } from "react";

export default function Header() {
const [time, setTime] = useState("");

useEffect(() => {
const update = () => {
setTime(new Date().toUTCString().split(" ")[4] + " UTC");
};
update();
const t = setInterval(update, 1000);
return () => clearInterval(t);
}, []);

return (
<header className="flex items-center justify-between px-6 py-3 border-b border-mad-border bg-mad-panel">
<div className="flex items-center gap-3">
<span className="text-lg font-bold text-white tracking-tight">MAD</span>
<span className="text-xs text-slate-400">— Mantle Anomaly Detector · Mantle Network</span>
</div>
<div className="flex items-center gap-2 text-xs">
<span className="w-2 h-2 rounded-full bg-green-500 pulse-red inline-block" />
<span className="text-green-400 font-semibold">LIVE</span>
<span className="text-slate-400 ml-2">{time}</span>
</div>
</header>
);
}
