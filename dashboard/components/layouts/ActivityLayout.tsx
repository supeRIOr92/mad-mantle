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
import SectionHeader from "@/components/SectionHeader";
import Footer from "@/components/Footer";

export default function ActivityLayout() {
  return (
    <main className="flex-1 flex flex-col">
      <div className="flex-1 p-3 sm:p-4 space-y-5">

        {/* ── SYSTEM STATUS ── */}
        <section>
          <SectionHeader
            title="System Status"
            subtitle="Real-time scanner health and data pipeline indicators"
            accent="slate"
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
            <PanelSystemStatus />
            <PanelEcosystemHealth />
            <PanelModelStatus />
          </div>
        </section>

        {/* ── MARKET MONITOR ── */}
        <section>
          <SectionHeader
            title="Market Monitor"
            subtitle="Live swap activity and pool-level anomaly signals"
            accent="cyan"
          />
          <div
            className="grid gap-3 mt-3"
            style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}
          >
            <Panel2LiveFeed />
            <PanelTopRiskPools />
            <Panel5AgentReport />
          </div>
        </section>

        {/* ── ECOSYSTEM INTELLIGENCE ── */}
        <section>
          <SectionHeader
            title="Ecosystem Intelligence"
            subtitle="Agent activity, smart money positioning, and volume analysis"
            accent="cyan"
          />
          <div
            className="grid gap-3 mt-3"
            style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}
          >
            <Panel4SmartMoney />
            <Panel6BubbleChart />
            <Panel7VolumeChart />
          </div>
        </section>

      </div>
      <Footer />
    </main>
  );
}
