"use client";
import Panel2LiveFeed from "@/components/Panel2LiveFeed";
import Panel4SmartMoney from "@/components/Panel4SmartMoney";
import Panel5AgentReport from "@/components/Panel5AgentReport";
import Panel6BubbleChart from "@/components/Panel6BubbleChart";
import Panel7VolumeChart from "@/components/Panel7VolumeChart";
import PanelSystemStatus from "@/components/PanelSystemStatus";
import PanelEcosystemHealth from "@/components/PanelEcosystemHealth";
import PanelModelStatus from "@/components/PanelModelStatus";
import PanelTopRiskPools from "@/components/PanelTopRiskPools";

export default function ActivityLayout() {
return (
<main className="flex-1 p-4 space-y-3">
{/* Row 1 — Status Layer */}
<div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1.5fr 1fr" }}>
<PanelSystemStatus />
<PanelEcosystemHealth />
<PanelModelStatus />
</div>

{/* Row 2 — Flow Layer */}
<div className="grid gap-3" style={{ gridTemplateColumns: "1.5fr 1fr 1fr" }}>
<Panel2LiveFeed />
<PanelTopRiskPools />
<Panel5AgentReport />
</div>

{/* Row 3 — Behavior Layer */}
<div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr 1.5fr" }}>
<Panel4SmartMoney />
<Panel6BubbleChart />
<Panel7VolumeChart />
</div>
</main>
);
}
