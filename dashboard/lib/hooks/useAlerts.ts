import { useEffect, useState } from "react";
import { supabase, type Signal } from "@/lib/supabase";
import { useAppState } from "@/lib/app-state";

export function useAlerts(limit = 20) {
const { mode } = useAppState();
const [alerts, setAlerts] = useState<Signal[]>([]);
const [signals, setSignals] = useState<Signal[]>([]);

const fetchData = async () => {
const { data: alertData } = await supabase
.from("signal_log")
.select("*")
.in("alert_level", ["alert", "high_conf"])
.eq("environment", mode)
.order("created_at", { ascending: false })
.limit(limit);
if (alertData) setAlerts(alertData as Signal[]);

const { data: signalData } = await supabase
.from("signal_log")
.select("*")
.eq("alert_level", "watching")
.eq("environment", mode)
.order("created_at", { ascending: false })
.limit(limit);
if (signalData) setSignals(signalData as Signal[]);
};

useEffect(() => {
fetchData();
const interval = setInterval(fetchData, 5000);
return () => clearInterval(interval);
}, [mode, limit]);

return { alerts, signals };
}