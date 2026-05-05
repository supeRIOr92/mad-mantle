"use client";

import { useEffect, useState } from "react";
import { useAppState } from "@/lib/app-state";
import { usePoolScans } from "@/lib/hooks/usePoolScans";

function aaveBadgeColor(label: string) {
  if (label === "FLASH_LOAN_LARGE" || label === "FLASH_LOAN") return "text-red-400";
  if (label === "BORROW_LARGE" || label === "BORROW_MID") return "text-orange-400";
  if (label === "BORROW_SMALL") return "text-yellow-400";
  return "text-green-400";
}

export default function PanelSystemStatus() {
  const { mode } = useAppState();
  const { scans } = usePoolScans(10);
  const [uptime, setUptime] = useState("00:00:00");
  const [startTime] = useState(Date.now());

  useEffect(() => {
    const t = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const h = Math.floor(elapsed / 3600).toString().padStart(2, "0");
      const m = Math.floor((elapsed % 3600) / 60).toString().padStart(2, "0");
      const s = (elapsed % 60).toString().padStart(2, "0");
      setUptime(`${h}:${m}:${s}`);
    }, 1000);
    return () => clearInterval(t);
  }, [startTime]);

  const lastScan = scans[0] ? new Date(scans[0].created_at) : null;
  const secondsAgo = lastScan
    ? Math.floor((Date.now() - lastScan.getTime()) / 1000)
    : null;

  const lastScanLabel =
    secondsAgo === null
      ? "No scans yet"
      : secondsAgo < 60
      ? `${secondsAgo}s ago`
      : `${Math.floor(secondsAgo / 60)}m ago`;

  const hasAlert = scans.some(
    (s) => s.alert_level === "alert" || s.alert_level === "high_conf"
  );

  const latestAaveLabel = scans[0]?.aave_label ?? "NO_DATA";
  const latestAaveSignal = scans[0]?.aave_signal ?? 0;
  const aaveActive = latestAaveSignal > 0;

  return (
    <div className="panel h-full">
      <div className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-4">
        System Status
      </div>

      {/* Status indicator */}
      <div className="flex items-center gap-2 mb-4">
        <span
          className={`w-3 h-3 rounded-full inline-block ${
            hasAlert ? "bg-red-500" : "bg-green-500"
          }`}
        />
        <span
          className={`text-sm font-bold ${
            hasAlert ? "text-red-400" : "text-green-400"
          }`}
        >
          {hasAlert ? "ANOMALY DETECTED" : "SYSTEM ACTIVE"}
        </span>
      </div>

      {/* Metrics */}
      <div className="space-y-2 text-[11px]">
        <div className="flex justify-between border-b border-mad-border/50 pb-1">
          <span className="text-slate-500">Mode</span>
          <span
            className={
              mode === "demo"
                ? "text-amber-400 font-semibold"
                : "text-green-400 font-semibold"
            }
          >
            {mode.toUpperCase()}
          </span>
        </div>

        <div className="flex justify-between border-b border-mad-border/50 pb-1">
          <span className="text-slate-500">DEXes monitored</span>
          <span className="text-white">
          <span className="text-red-400">Agni ✗</span>
          {" · "}
          <span className="text-green-400">Moe ✓</span>
          {" · "}
          <span className="text-green-400">Fluxion ✓</span>
          </span>
        </div>

        <div className="flex justify-between border-b border-mad-border/50 pb-1">
          <span className="text-slate-500">Aave signal</span>
          <span className={`font-semibold ${aaveBadgeColor(latestAaveLabel)}`}>
            {aaveActive ? latestAaveLabel.replace(/_/g, " ") : "CLEAN"}
          </span>
        </div>

        <div className="flex justify-between border-b border-mad-border/50 pb-1">
          <span className="text-slate-500">Last scan</span>
          <span className="text-white">{lastScanLabel}</span>
        </div>

        <div className="flex justify-between border-b border-mad-border/50 pb-1">
          <span className="text-slate-500">Session uptime</span>
          <span className="text-white font-mono">{uptime}</span>
        </div>

        <div className="flex justify-between pb-1">
          <span className="text-slate-500">Total scans</span>
          <span className="text-white">{scans.length}</span>
        </div>
      </div>

      {!hasAlert && (
        <p className="text-[10px] text-slate-600 mt-3">
          No anomalies detected — all pools within baseline
        </p>
      )}
    </div>
  );
}