"use client";
import { createContext, useContext, useState, ReactNode } from "react";

type Mode = "live" | "demo";
type View = "activity" | "risk";

interface AppState {
mode: Mode;
setMode: (m: Mode) => void;
view: View;
setView: (v: View) => void;
}

const AppStateContext = createContext<AppState>({
mode: "live",
setMode: () => {},
view: "activity",
setView: () => {},
});

export function AppStateProvider({ children }: { children: ReactNode }) {
const [mode, setMode] = useState<Mode>("live");
const [view, setView] = useState<View>("activity");

return (
<AppStateContext.Provider value={{ mode, setMode, view, setView }}>
{children}
</AppStateContext.Provider>
);
}

export function useAppState() {
return useContext(AppStateContext);
}