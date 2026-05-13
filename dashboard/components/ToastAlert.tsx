"use client";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useAppState } from "@/lib/app-state";

interface ToastData {
  s_final: number;
  alert_level: string;
  pools: number;
  created_at: string;
}

export default function ToastAlert() {
  const { mode } = useAppState();
  const [toast, setToast] = useState<{ message: string; type: "info" | "warning" | "alert" } | null>(null);
  const [visible, setVisible] = useState(false);
  const [shown, setShown] = useState(false); // only show on-load once
  const [lastAlertLevel, setLastAlertLevel] = useState<string>("none");

  const dismiss = () => {
    setVisible(false);
    setTimeout(() => setToast(null), 300);
  };

  const showToast = (message: string, type: "info" | "warning" | "alert") => {
    setToast({ message, type });
    setVisible(true);
    if (type === "info") {
      setTimeout(dismiss, 6000); // auto-dismiss info after 6s
    }
  };

  useEffect(() => {
    const load = async () => {
      const { data: signals } = await supabase
        .from("signal_log")
        .select("s_final, alert_level, created_at")
        .eq("environment", mode)
        .order("created_at", { ascending: false })
        .limit(1);

      if (!signals || !signals[0]) return;
      const latest = signals[0];

      // On-load toast (once per session)
      if (!shown) {
        setShown(true);
        const statusText =
          latest.alert_level === "none" && latest.s_final < 20
            ? "Normal — tidak ada anomaly terdeteksi."
            : latest.alert_level === "watching"
            ? `Elevated — s_final=${latest.s_final.toFixed(1)}, dalam pengawasan.`
            : `ALERT — s_final=${latest.s_final.toFixed(1)}, anomaly terdeteksi.`;

        showToast(`MAD aktif · ${statusText}`, "info");
        setLastAlertLevel(latest.alert_level);
        return;
      }

      // Subsequent check — only toast if alert level changed to something notable
      if (
        latest.alert_level !== lastAlertLevel &&
        latest.alert_level !== "none"
      ) {
        setLastAlertLevel(latest.alert_level);
        if (latest.alert_level === "watching") {
          showToast(
            `⚠ WATCHING — s_final=${latest.s_final.toFixed(1)} melewati threshold. Pool sedang dipantau ketat.`,
            "warning"
          );
        } else if (latest.alert_level === "alert" || latest.alert_level === "high_conf") {
          showToast(
            `🚨 ALERT — s_final=${latest.s_final.toFixed(1)}. Manipulation pattern terdeteksi. Cek Risk View.`,
            "alert"
          );
        }
      } else {
        setLastAlertLevel(latest.alert_level);
      }
    };

    load();
    const interval = setInterval(load, 20000);
    return () => clearInterval(interval);
  }, [mode, shown, lastAlertLevel]);

  if (!toast) return null;

  const bgMap = {
    info: "bg-slate-900 border-slate-700",
    warning: "bg-amber-950/80 border-amber-700/60",
    alert: "bg-red-950/80 border-red-700/60",
  };

  const textMap = {
    info: "text-slate-300",
    warning: "text-amber-300",
    alert: "text-red-300",
  };

  const dotMap = {
    info: "bg-slate-400",
    warning: "bg-amber-400",
    alert: "bg-red-400 animate-pulse",
  };

  return (
    <div
      className={`fixed bottom-5 right-5 z-50 max-w-sm transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"
      }`}
    >
      <div className={`border rounded-lg px-4 py-3 shadow-xl ${bgMap[toast.type]}`}>
        <div className="flex items-start gap-3">
          <div className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${dotMap[toast.type]}`} />
          <div className="flex-1 min-w-0">
            <p className={`text-xs leading-relaxed ${textMap[toast.type]}`}>
              {toast.message}
            </p>
          </div>
          <button
            onClick={dismiss}
            className="text-slate-600 hover:text-slate-400 text-xs ml-2 flex-shrink-0"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}
