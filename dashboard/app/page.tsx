"use client";
import { useAppState } from "@/lib/app-state";
import Header from "@/components/Header";
import DemoControlPanel from "@/components/DemoControlPanel";
import ActivityLayout from "@/components/layouts/ActivityLayout";
import RiskLayout from "@/components/layouts/RiskLayout";
import TickerBar from "@/components/TickerBar";
import ToastAlert from "@/components/ToastAlert";

export default function Dashboard() {
  const { mode, view } = useAppState();

  return (
    <div className="min-h-screen bg-mad-bg flex flex-col">
      <Header />
      <TickerBar />
      {mode === "demo" && <DemoControlPanel />}
      {view === "activity" ? <ActivityLayout /> : <RiskLayout />}
      <ToastAlert />
    </div>
  );
}
