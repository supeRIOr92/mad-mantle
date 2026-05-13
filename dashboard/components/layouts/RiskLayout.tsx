"use client";
import Panel2LiveFeed from "@/components/Panel2LiveFeed";
import Panel4SmartMoney from "@/components/Panel4SmartMoney";
import Panel5AgentReport from "@/components/Panel5AgentReport";
import Panel7VolumeChart from "@/components/Panel7VolumeChart";
import PanelAlerts from "@/components/PanelAlerts";
import PanelSignals from "@/components/PanelSignals";
import PanelTopRiskPools from "@/components/PanelTopRiskPools";
import PanelEcosystemHealth from "@/components/PanelEcosystemHealth";
import SectionHeader from "@/components/SectionHeader";
import Footer from "@/components/Footer";

export default function RiskLayout() {
  return (
    <main className="flex-1 flex flex-col">
      <div className="flex-1 px-4 sm:px-8 lg:px-12 py-4 sm:py-6 space-y-6">

        {/* ── THREAT DETECTION ── */}
        <section>
          <SectionHeader
            title="Threat Detection"
            subtitle="Active manipulation signals and alert pipeline"
            accent="red"
          />
          <div
            className="grid gap-3 mt-3"
            style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}
          >
            <PanelAlerts />
            <PanelSignals />
          </div>
        </section>

        {/* ── WALLET INTELLIGENCE ── */}
        <section>
          <SectionHeader
            title="Wallet Intelligence"
            subtitle="Behavioral profiling — who's trading, and why it matters"
            accent="red"
          />
          <div
            className="grid gap-3 mt-3"
            style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}
          >
            <PanelTopRiskPools />
            <Panel4SmartMoney />
            <Panel5AgentReport />
          </div>
        </section>

        {/* ── AGENT FORENSICS ── */}
        <section>
          <SectionHeader
            title="Agent Forensics"
            subtitle="AI agent activity mapped to ERC-8004 identity registry"
            accent="slate"
          />
          <div
            className="grid gap-3 mt-3"
            style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}
          >
            <Panel2LiveFeed />
            <Panel7VolumeChart />
            <PanelEcosystemHealth />
          </div>
        </section>

      </div>
      <Footer />
    </main>
  );
}
