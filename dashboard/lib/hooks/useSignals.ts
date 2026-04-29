import { useEffect, useState } from "react";
import { supabase, type Signal } from "@/lib/supabase";

export function useSignals(limit = 20) {
const [signals, setSignals] = useState<Signal[]>([]);

useEffect(() => {
supabase
.from("signal_log")
.select("*")
.order("created_at", { ascending: false })
.limit(limit)
.then(({ data }) => { if (data) setSignals(data as Signal[]); });

const channel = supabase
.channel("hook-signals")
.on("postgres_changes", { event: "INSERT", schema: "public", table: "signal_log" },
(payload) => setSignals((prev) => [payload.new as Signal, ...prev].slice(0, limit))
)
.subscribe();

return () => { supabase.removeChannel(channel); };
}, [limit]);

return signals;
}