import Header from "@/components/Header";
import Panel1LiveScores from "@/components/Panel1LiveScores";
import Panel2LiveFeed from "@/components/Panel2LiveFeed";
import Panel3Accuracy from "@/components/Panel3Accuracy";
import Panel4SmartMoney from "@/components/Panel4SmartMoney";
import Panel5AgentReport from "@/components/Panel5AgentReport";
import Panel6BubbleChart from "@/components/Panel6BubbleChart";
import Panel7VolumeChart from "@/components/Panel7VolumeChart";

export default function Dashboard() {
return (
<div className="min-h-screen bg-mad-bg flex flex-col">
<Header />

<main className="flex-1 p-4 grid gap-3" style={{
gridTemplateColumns: "1fr 1.5fr 1fr",
gridTemplateRows: "auto auto auto",
}}>
{/* Row 1 */}
<Panel1LiveScores />
<Panel2LiveFeed />
<Panel3Accuracy />

{/* Row 2 */}
<Panel4SmartMoney />
<Panel5AgentReport />
<Panel6BubbleChart />

{/* Row 3 — full width */}
<div className="col-span-3">
<Panel7VolumeChart />
</div>
</main>
</div>
);
}
