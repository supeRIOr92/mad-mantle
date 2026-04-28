import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
title: "MAD — Mantle Anomaly Detector",
description: "AI Alpha & Risk Detection — Mantle Network",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
return (
<html lang="en">
<body>{children}</body>
</html>
);
}
