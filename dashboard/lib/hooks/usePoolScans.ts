import { useEffect, useState } from "react";
import { supabase, type Signal } from "@/lib/supabase";
import { useAppState } from "@/lib/app-state";

export function usePoolScans(limit = 48) {
  const { mode } = useAppState();
  const [scans, setScans] = useState<Signal[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);

  const fetchData = async () => {
    const { data } = await supabase
      .from("signal_log")
      .select("*")
      .eq("environment", mode)
      .order("created_at", { ascending: false })
      .limit(limit);

    if (data) setScans(data as Signal[]);
  };

  const fetchCount = async () => {
    const { count } = await supabase
      .from("signal_log")
      .select("*", { count: "exact", head: true })
      .eq("environment", mode);

    if (count !== null) setTotalCount(count);
  };

  useEffect(() => {
    fetchData();
    fetchCount();

    const interval = setInterval(() => {
      fetchData();
      fetchCount();
    }, 5000);

    return () => clearInterval(interval);
  }, [mode, limit]);

  const topRisk = (() => {
    const seen = new Set<string>();
    return scans
      .slice()
      .sort((a, b) => b.s_final - a.s_final)
      .filter((s) => {
        if (seen.has(s.pool_address)) return false;
        seen.add(s.pool_address);
        return true;
      })
      .slice(0, 5);
  })();

  const avgScore = scans.length
    ? Math.round(scans.reduce((acc, s) => acc + s.s_final, 0) / scans.length)
    : 0;

  const scoreTimeline = scans
    .slice()
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map((s) => ({
      time: new Date(s.created_at).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      score: Math.round(s.s_final),
    }));

  return { scans, totalCount, topRisk, avgScore, scoreTimeline };
}