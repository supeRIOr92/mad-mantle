"use client";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  accent?: "cyan" | "red" | "slate";
}

export default function SectionHeader({ title, subtitle, accent = "slate" }: SectionHeaderProps) {
  const accentMap = {
    cyan: "text-cyan-400 border-cyan-500/40",
    red: "text-red-400 border-red-500/40",
    slate: "text-slate-400 border-slate-600/40",
  };

  const barMap = {
    cyan: "bg-cyan-400",
    red: "bg-red-400",
    slate: "bg-slate-500",
  };

  return (
    <div className={`flex items-center gap-3 px-1 pt-3 pb-2 border-b ${accentMap[accent]}`}>
      <div className={`w-1.5 h-5 rounded-full flex-shrink-0 ${barMap[accent]}`} />
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className={`text-sm font-bold tracking-widest uppercase ${accentMap[accent].split(" ")[0]}`}>
          {title}
        </span>
        {subtitle && (
          <span className="text-xs text-slate-500 leading-tight break-words">{subtitle}</span>
        )}
      </div>
    </div>
  );
}
