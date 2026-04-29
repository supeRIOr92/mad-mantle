import { useEffect, useState } from "react";
import { supabase, type Wallet } from "@/lib/supabase";
import { useAppState } from "@/lib/app-state";

export function useWalletProfiles(limit = 10) {
const { mode } = useAppState();
const [wallets, setWallets] = useState<Wallet[]>([]);

const fetchData = async () => {
const { data } = await supabase
.from("wallet_profile")
.select("*")
.eq("environment", mode)
.order("smart_score", { ascending: false, nullsFirst: false })
.limit(limit);
if (data) setWallets(data as Wallet[]);
};

useEffect(() => {
fetchData();
const interval = setInterval(fetchData, 5000);
return () => clearInterval(interval);
}, [mode, limit]);

const manipulators = wallets.filter((w) => w.agent_type === "MANIPULATOR");
const smartMoney = wallets.filter((w) => w.agent_type !== "MANIPULATOR");
const topRisky = wallets
.slice()
.sort((a, b) => (b.wash_ratio || 0) - (a.wash_ratio || 0))
.slice(0, 5);

return { wallets, manipulators, smartMoney, topRisky };
}