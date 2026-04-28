import type { Config } from "tailwindcss";

const config: Config = {
content: [
"./app/**/*.{js,ts,jsx,tsx,mdx}",
"./components/**/*.{js,ts,jsx,tsx,mdx}",
],
theme: {
extend: {
colors: {
mad: {
bg: "#0a0a0f",
panel: "#0f0f1a",
border: "#1a1a2e",
red: "#ef4444",
yellow: "#eab308",
green: "#22c55e",
cyan: "#06b6d4",
purple: "#8b5cf6",
},
},
fontFamily: {
mono: ["JetBrains Mono", "Fira Code", "monospace"],
},
},
},
plugins: [],
};

export default config;
