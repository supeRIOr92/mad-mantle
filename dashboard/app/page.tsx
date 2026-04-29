"use client";
import { useAppState } from "@/lib/app-state";
import Header from "@/components/Header";
import DemoControlPanel from "@/components/DemoControlPanel";
import ActivityLayout from "@/components/layouts/ActivityLayout";
import RiskLayout from "@/components/layouts/RiskLayout";

export default function Dashboard() {
const { mode, view } = useAppState();

return (
<div className="min-h-screen bg-mad-bg flex flex-col">
<Header />
{mode === "demo" && <DemoControlPanel />}
{view === "activity" ? <ActivityLayout /> : <RiskLayout />}
</div>
);
}