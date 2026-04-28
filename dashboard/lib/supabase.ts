import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(url, key, {
realtime: { params: { eventsPerSecond: 10 } },
});

export type Signal = {
id: number;
created_at: string;
dex: string;
pool_address: string;
tx_hashes: string[];
l1_score: number;
l2_score: number;
l3_score: number;
s_dex: number;
s_final: number;
alert_level: "watching" | "alert" | "high_conf" | "none";
l1_methods: any[];
l2_methods: any[];
l3_methods: any[];
top_wallets: any[];
volume_usd: number;
corroboration: number;
phase1_active: boolean;
};

export type Wallet = {
address: string;
agent_type: string;
archetype: string;
roi_7d: number | null;
smart_score: number | null;
wash_ratio: number;
wash_label: string;
rep_score: number | null;
reputation_score: number | null;
aave_modifier: number;
total_volume_usd: number;
tx_count: number;
risk_label: string;
agent_token_id: string | null;
};
