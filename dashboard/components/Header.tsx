"use client";
import { useEffect, useState } from "react";
import { useAppState } from "@/lib/app-state";

export default function Header() {
  const [time, setTime] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
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
    <div
      className={`border-b border-mad-border transition-colors ${
        mode === "demo" ? "bg-amber-950/20" : "bg-mad-panel"
      }`}
    >
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-2.5">
        {/* Left: Branding */}
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-white tracking-tight">MAD</span>
          <span className="text-xs text-slate-400 hidden sm:inline">
            — Mantle Anomaly Detector
          </span>
          {mode === "demo" && (
            <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/40 px-2 py-0.5 rounded font-bold">
              DEMO MODE
            </span>
          )}
        </div>

        {/* Right: Desktop controls + status */}
        <div className="flex items-center gap-3">
          {/* Mode Toggle — desktop */}
          <div className="hidden sm:flex items-center gap-1">
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

          {/* Status dot + time */}
          <div className="hidden sm:flex items-center gap-2 text-xs ml-1">
            <span
              className={`w-2 h-2 rounded-full inline-block ${
                mode === "demo" ? "bg-amber-400" : "bg-green-500 pulse-red"
              }`}
            />
            <span
              className={
                mode === "demo"
                  ? "text-amber-400 font-semibold"
                  : "text-green-400 font-semibold"
              }
            >
              {mode === "demo" ? "DEMO" : "LIVE"}
            </span>
            <span className="text-slate-400 ml-1">{time}</span>
          </div>

          {/* Mobile: time only */}
          <span className="text-[10px] text-slate-400 sm:hidden">{time}</span>

          {/* Mobile: hamburger */}
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="sm:hidden flex flex-col gap-1 p-1"
            aria-label="Menu"
          >
            <span className="w-5 h-0.5 bg-slate-400 rounded" />
            <span className="w-5 h-0.5 bg-slate-400 rounded" />
            <span className="w-5 h-0.5 bg-slate-400 rounded" />
          </button>
        </div>
      </div>

      {/* Second Bar — View Switch + Whitepaper (desktop) */}
      <div className="hidden sm:flex items-center gap-1 px-6 pb-2">
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
        <a
          href="/whitepaper"
          className="text-[10px] px-3 py-1 rounded font-bold border border-transparent text-slate-500 hover:text-cyan-400 hover:border-cyan-500/40 transition-all ml-1"
        >
          Whitepaper
        </a>
        <span className="text-slate-700 text-xs ml-2">|</span>
        <span className="text-[10px] text-slate-600 ml-2">
          {view === "activity" ? "Ecosystem monitoring" : "Anomaly & decision layer"}
        </span>
      </div>

      {/* Mobile Dropdown Menu */}
      {menuOpen && (
        <div className="sm:hidden border-t border-mad-border px-4 py-3 space-y-3">
          {/* View toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => { setView("activity"); setMenuOpen(false); }}
              className={`flex-1 text-[10px] py-1.5 rounded font-bold border transition-all ${
                view === "activity"
                  ? "bg-slate-600/40 text-slate-200 border-slate-500"
                  : "bg-transparent text-slate-500 border-slate-700"
              }`}
            >
              Activity View
            </button>
            <button
              onClick={() => { setView("risk"); setMenuOpen(false); }}
              className={`flex-1 text-[10px] py-1.5 rounded font-bold border transition-all ${
                view === "risk"
                  ? "bg-red-500/20 text-red-400 border-red-500/40"
                  : "bg-transparent text-slate-500 border-slate-700"
              }`}
            >
              Risk View
            </button>
          </div>
          {/* Mode toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => { setMode("live"); setMenuOpen(false); }}
              className={`flex-1 text-[10px] py-1.5 rounded font-bold border transition-all ${
                mode === "live"
                  ? "bg-green-500/20 text-green-400 border-green-500/40"
                  : "bg-transparent text-slate-500 border-slate-700"
              }`}
            >
              LIVE
            </button>
            <button
              onClick={() => { setMode("demo"); setMenuOpen(false); }}
              className={`flex-1 text-[10px] py-1.5 rounded font-bold border transition-all ${
                mode === "demo"
                  ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                  : "bg-transparent text-slate-500 border-slate-700"
              }`}
            >
              DEMO
            </button>
          </div>
          {/* Whitepaper link */}
          <a
            href="/whitepaper"
            onClick={() => setMenuOpen(false)}
            className="block text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            → Whitepaper
          </a>
        </div>
      )}
    </div>
  );
}
