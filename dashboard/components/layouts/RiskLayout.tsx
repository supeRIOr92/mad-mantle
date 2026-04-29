"use client";
import Panel2LiveFeed from "@/components/Panel2LiveFeed";
import Panel4SmartMoney from "@/components/Panel4SmartMoney";
import Panel5AgentReport from "@/components/Panel5AgentReport";
import Panel7VolumeChart from "@/components/Panel7VolumeChart";
import PanelAlerts from "@/components/PanelAlerts";
import PanelSignals from "@/components/PanelSignals";
import PanelTopRiskPools from "@/components/PanelTopRiskPools";
import PanelEcosystemHealth from "@/components/PanelEcosystemHealth";

export default function RiskLayout() {
return (
<main className="flex-1 p-4 space-y-3">
{/* Row 1 — Critical Layer */}
<div className="grid gap-3" style={{ gridTemplateColumns: "1.5fr 1fr" }}>
<PanelAlerts />
<PanelSignals />
</div>

{/* Row 2 — Context Layer */}
<div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
<PanelTopRiskPools />
<Panel4SmartMoney />
<Panel5AgentReport />
</div>

{/* Row 3 — Supporting Layer */}
<div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1.5fr 1fr" }}>
<Panel2LiveFeed />
<Panel7VolumeChart />
<PanelEcosystemHealth />
</div>
</main>
);
}
