import type { Metadata } from "next";
import "./globals.css";
import { AppStateProvider } from "@/lib/app-state";

export const metadata: Metadata = {
title: "MAD — Mantle Anomaly Detector",
description: "AI Alpha & Risk Detection — Mantle Network",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
return (
<html lang="en">
<body>
<AppStateProvider>
{children}
</AppStateProvider>
</body>
</html>
);
}
