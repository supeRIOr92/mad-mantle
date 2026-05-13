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
    <div className={`flex items-center gap-3 px-1 pt-2 pb-1 border-b ${accentMap[accent]}`}>
      <div className={`w-1 h-4 rounded-full flex-shrink-0 ${barMap[accent]}`} />
      <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3 min-w-0">
        <span className={`text-[10px] font-bold tracking-widest uppercase ${accentMap[accent].split(" ")[0]}`}>
          {title}
        </span>
        {subtitle && (
          <span className="text-[10px] text-slate-600 hidden sm:inline truncate">— {subtitle}</span>
        )}
      </div>
    </div>
  );
}
