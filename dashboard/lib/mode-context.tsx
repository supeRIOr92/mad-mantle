"use client";
import { createContext, useContext, useState, ReactNode } from "react";

type Mode = "live" | "demo";

const ModeContext = createContext<{
mode: Mode;
setMode: (m: Mode) => void;
}>({
mode: "live",
setMode: () => {},
});

export function ModeProvider({ children }: { children: ReactNode }) {
const [mode, setMode] = useState<Mode>("live");
return (
<ModeContext.Provider value={{ mode, setMode }}>
{children}
</ModeContext.Provider>
);
}

export function useMode() {
return useContext(ModeContext);
}
