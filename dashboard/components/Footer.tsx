"use client";

export default function Footer() {
  return (
    <footer className="border-t border-mad-border bg-mad-panel mt-4 px-4 sm:px-6 py-4">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Branding */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-white tracking-tight">MAD</span>
          <span className="text-[10px] text-slate-500">Mantle Anomaly Detector</span>
          <span className="text-slate-700 text-xs">·</span>
          <span className="text-[10px] text-slate-600">v2.0</span>
        </div>

        {/* Nav Links */}
        <div className="flex items-center gap-4">
          <a
            href="/"
            className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            Dashboard
          </a>
          <a
            href="/whitepaper"
            className="text-[10px] text-slate-500 hover:text-cyan-400 transition-colors"
          >
            Whitepaper
          </a>
          <a
            href="https://github.com/supeRIOr92/mad-mantle"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            GitHub
          </a>
        </div>

        {/* Powered by */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-600">Powered by</span>
          <span className="text-[10px] font-semibold text-slate-400">Mantle Network</span>
        </div>
      </div>
    </footer>
  );
}
