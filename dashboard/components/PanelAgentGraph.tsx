"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { supabase, type Signal, type Wallet } from "@/lib/supabase";
import { useAppState } from "@/lib/app-state";

// ── Types ──────────────────────────────────────────────────────────────────
interface GraphNode {
  id: string;
  label: string;
  agentType: string;
  archetype: string;
  txCount: number;
  smartScore: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  aaveOverlap: boolean;
}

// ── Constants ──────────────────────────────────────────────────────────────
const MIN_SHARED_WINDOWS = 2;
const WINDOW_MINUTES = 15;

const AGENT_COLORS: Record<string, string> = {
  "Registered Agent":        "#22d3ee",
  "Probable Automation":     "#a78bfa",
  "Suspicious Coordination": "#f87171",
  "SMART MONEY":             "#34d399",
  "Unclassified":            "#64748b",
};

const ARCHETYPE_COLORS: Record<string, string> = {
  FLASH_WASH:        "#f87171",
  COORDINATED_WASH:  "#fb923c",
  PUMP_DUMP:         "#facc15",
  COMPLEX_MULTI_DEX: "#a78bfa",
  ARB_PATTERN:       "#22d3ee",
};

function getNodeColor(node: GraphNode): string {
  if (ARCHETYPE_COLORS[node.archetype]) return ARCHETYPE_COLORS[node.archetype];
  return AGENT_COLORS[node.agentType] ?? "#64748b";
}

// ── Co-occurrence Builder ──────────────────────────────────────────────────
function buildGraph(signals: Signal[], wallets: Wallet[]): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const walletMap = new Map<string, Wallet>();
  wallets.forEach((w) => walletMap.set(w.address.toLowerCase(), w));

  const coOccur = new Map<string, { count: number; windowSizes: number[]; aaveOverlap: boolean }>();

  signals.forEach((sig) => {
    const topWallets: string[] = (sig.top_wallets ?? [])
      .map((w: any) => (typeof w === "string" ? w : w?.address ?? w?.id ?? ""))
      .filter(Boolean)
      .map((a: string) => a.toLowerCase());

    if (topWallets.length < 2) return;

    const windowSize = topWallets.length;

    for (let i = 0; i < topWallets.length; i++) {
      for (let j = i + 1; j < topWallets.length; j++) {
        const a = topWallets[i];
        const b = topWallets[j];
        const key = [a, b].sort().join("|");
        const existing = coOccur.get(key);

        const wA = walletMap.get(a);
        const wB = walletMap.get(b);
        const aaveOverlap =
          (wA?.aave_modifier ?? 1) > 1.2 && (wB?.aave_modifier ?? 1) > 1.2;

        if (existing) {
          existing.count += 1;
          existing.windowSizes.push(windowSize);
          existing.aaveOverlap = existing.aaveOverlap || aaveOverlap;
        } else {
          coOccur.set(key, { count: 1, windowSizes: [windowSize], aaveOverlap });
        }
      }
    }
  });

  const validPairs = Array.from(coOccur.entries()).filter(
    ([, v]) => v.count >= MIN_SHARED_WINDOWS
  );

  if (validPairs.length === 0) return { nodes: [], edges: [] };

  const activeAddresses = new Set<string>();
  validPairs.forEach(([key]) => {
    const [a, b] = key.split("|");
    activeAddresses.add(a);
    activeAddresses.add(b);
  });

  const centerX = 400;
  const centerY = 300;
  const r = Math.min(220, 40 * activeAddresses.size);
  const nodes: GraphNode[] = Array.from(activeAddresses).map((addr, i) => {
    const angle = (2 * Math.PI * i) / activeAddresses.size;
    const wallet = walletMap.get(addr);
    return {
      id: addr,
      label: addr.slice(0, 6) + "…" + addr.slice(-4),
      agentType: wallet?.agent_type ?? "Unclassified",
      archetype: wallet?.archetype ?? "",
      txCount: wallet?.tx_count ?? 1,
      smartScore: wallet?.smart_score ?? 0,
      x: centerX + r * Math.cos(angle),
      y: centerY + r * Math.sin(angle),
      vx: 0,
      vy: 0,
      radius: Math.max(8, Math.min(20, 8 + (wallet?.tx_count ?? 1) * 0.5)),
    };
  });

  const edges: GraphEdge[] = validPairs.map(([key, v]) => {
    const [source, target] = key.split("|");
    const avgWindowSize =
      v.windowSizes.reduce((s, x) => s + x, 0) / v.windowSizes.length;
    const weight = v.count / avgWindowSize;
    return { source, target, weight, aaveOverlap: v.aaveOverlap };
  });

  return { nodes, edges };
}

// ── Force Layout ───────────────────────────────────────────────────────────
function applyForces(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number): GraphNode[] {
  const REPEL = 3000;
  const SPRING_K = 0.04;
  const SPRING_LEN = 120;
  const DAMP = 0.7;
  const CENTER_PULL = 0.01;

  const next = nodes.map((n) => ({ ...n }));

  for (let i = 0; i < next.length; i++) {
    for (let j = i + 1; j < next.length; j++) {
      const dx = next[i].x - next[j].x;
      const dy = next[i].y - next[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = REPEL / (dist * dist);
      next[i].vx += (dx / dist) * force;
      next[i].vy += (dy / dist) * force;
      next[j].vx -= (dx / dist) * force;
      next[j].vy -= (dy / dist) * force;
    }
  }

  const nodeIndex = new Map(next.map((n, i) => [n.id, i]));
  edges.forEach((e) => {
    const si = nodeIndex.get(e.source);
    const ti = nodeIndex.get(e.target);
    if (si === undefined || ti === undefined) return;
    const dx = next[ti].x - next[si].x;
    const dy = next[ti].y - next[si].y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = SPRING_K * (dist - SPRING_LEN) * e.weight;
    next[si].vx += (dx / dist) * force;
    next[si].vy += (dy / dist) * force;
    next[ti].vx -= (dx / dist) * force;
    next[ti].vy -= (dy / dist) * force;
  });

  next.forEach((n) => {
    n.vx += (width / 2 - n.x) * CENTER_PULL;
    n.vy += (height / 2 - n.y) * CENTER_PULL;
    n.vx *= DAMP;
    n.vy *= DAMP;
    n.x = Math.max(n.radius, Math.min(width - n.radius, n.x + n.vx));
    n.y = Math.max(n.radius, Math.min(height - n.radius, n.y + n.vy));
  });

  return next;
}

// ── Canvas Renderer ────────────────────────────────────────────────────────
function renderGraph(
  ctx: CanvasRenderingContext2D,
  nodes: GraphNode[],
  edges: GraphEdge[],
  hoveredNode: string | null,
  width: number,
  height: number
) {
  ctx.clearRect(0, 0, width, height);

  const nodePos = new Map(nodes.map((n) => [n.id, n]));
  edges.forEach((e) => {
    const s = nodePos.get(e.source);
    const t = nodePos.get(e.target);
    if (!s || !t) return;

    const alpha = Math.min(0.8, 0.15 + e.weight * 0.3);
    const lineWidth = Math.min(3, 0.5 + e.weight);

    if (e.aaveOverlap) {
      ctx.save();
      ctx.shadowColor = "#22d3ee";
      ctx.shadowBlur = 8;
      ctx.strokeStyle = `rgba(34,211,238,${alpha})`;
      ctx.lineWidth = lineWidth + 1;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
      ctx.restore();
    } else {
      ctx.strokeStyle = `rgba(148,163,184,${alpha})`;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    }
  });

  nodes.forEach((n) => {
    const color = getNodeColor(n);
    const isHovered = n.id === hoveredNode;

    if (isHovered) {
      ctx.save();
      ctx.shadowColor = color;
      ctx.shadowBlur = 16;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 4, 0, Math.PI * 2);
      ctx.fillStyle = color + "33";
      ctx.fill();
      ctx.restore();
    }

    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
    ctx.fillStyle = color + (isHovered ? "ff" : "cc");
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.fillStyle = isHovered ? "#ffffff" : "#94a3b8";
    ctx.font = isHovered ? "bold 10px monospace" : "9px monospace";
    ctx.textAlign = "center";
    ctx.fillText(n.label, n.x, n.y + n.radius + 12);
  });
}

// ── Main Component ─────────────────────────────────────────────────────────
export default function PanelAgentGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedWallet, setSelectedWallet] = useState<Wallet | null>(null);
  const [selectedSignals, setSelectedSignals] = useState<Partial<Signal>[]>([]);
  const [isEmpty, setIsEmpty] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 420 });
  const { mode } = useAppState();

  useEffect(() => {
    const load = async () => {
      const [{ data: signals }, { data: wallets }] = await Promise.all([
        supabase
          .from("signal_log")
          .select("top_wallets, created_at, environment")
          .eq("environment", mode)
          .order("created_at", { ascending: false })
          .limit(50),
        supabase
          .from("wallet_profile")
          .select("*")
          .eq("environment", mode)
          .limit(200),
      ]);

      const { nodes, edges } = buildGraph(
        (signals ?? []) as Signal[],
        (wallets ?? []) as Wallet[]
      );

      nodesRef.current = nodes;
      edgesRef.current = edges;
      setIsEmpty(nodes.length === 0);
    };

    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [mode]);

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      setDimensions({ width: Math.floor(width), height: Math.floor(width * 0.5) });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    const animate = () => {
      if (nodesRef.current.length > 0 && frame < 300) {
        nodesRef.current = applyForces(
          nodesRef.current,
          edgesRef.current,
          dimensions.width,
          dimensions.height
        );
        frame++;
      }
      renderGraph(ctx, nodesRef.current, edgesRef.current, hoveredNode, dimensions.width, dimensions.height);
      animRef.current = requestAnimationFrame(animate);
    };
    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [hoveredNode, dimensions]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const scaleX = dimensions.width / rect.width;
      const scaleY = dimensions.height / rect.height;
      const mx = (e.clientX - rect.left) * scaleX;
      const my = (e.clientY - rect.top) * scaleY;

      const hit = nodesRef.current.find((n) => {
        const dx = n.x - mx;
        const dy = n.y - my;
        return Math.sqrt(dx * dx + dy * dy) <= n.radius + 4;
      });

      setHoveredNode(hit?.id ?? null);
      setTooltip(hit ? { x: e.clientX - rect.left, y: e.clientY - rect.top, node: hit } : null);
    },
    [dimensions]
  );

  const handleMouseLeave = useCallback(() => {
    setHoveredNode(null);
    setTooltip(null);
  }, []);

  const handleClick = useCallback(
    async (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const scaleX = dimensions.width / rect.width;
      const scaleY = dimensions.height / rect.height;
      const mx = (e.clientX - rect.left) * scaleX;
      const my = (e.clientY - rect.top) * scaleY;

      const hit = nodesRef.current.find((n) => {
        const dx = n.x - mx;
        const dy = n.y - my;
        return Math.sqrt(dx * dx + dy * dy) <= n.radius + 4;
      });
      console.log("click mx/my:", mx, my, "hit:", hit?.id ?? "none", "nodes:", nodesRef.current.length);
      if (!hit) {
        setSelectedNode(null);
        setSelectedWallet(null);
        setSelectedSignals([]);
        return;
      }
      
      setSelectedNode(hit);

      const { data: wData } = await supabase
        .from("wallet_profile")
        .select("*")
        .eq("address", hit.id)
        .limit(1);
      setSelectedWallet(wData?.[0] ?? null);

      const { data: sData } = await supabase
        .from("signal_log")
        .select("id,created_at,dex,pool_address,s_final,alert_level,volume_usd,top_wallets")
        .eq("environment", mode)
        .order("created_at", { ascending: false })
        .limit(100);

      const filtered = (sData ?? []).filter((sig: any) =>
        (sig.top_wallets ?? []).some((w: any) => {
          const addr = typeof w === "string" ? w : (w?.address ?? w?.id ?? w?.wallet ?? "");
          return addr.toLowerCase() === hit.id;
        })
      );
      setSelectedSignals(filtered.slice(0, 5) as Partial<Signal>[]);
    },
    [mode, dimensions]
  );

  return (
    <div className="bg-[#0D1117] border border-slate-800 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold text-slate-200 tracking-wide uppercase">
            Agent Coordination Graph
          </h3>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Behavioral affinity — wallets active in same pool within 15-min windows
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-3">
            {Object.entries(AGENT_COLORS).slice(0, 3).map(([label, color]) => (
              <div key={label} className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                <span className="text-[9px] text-slate-500">{label}</span>
              </div>
            ))}
            <div className="flex items-center gap-1">
              <div
                className="w-8 h-0.5 rounded"
                style={{ background: "rgba(34,211,238,0.8)", boxShadow: "0 0 4px #22d3ee" }}
              />
              <span className="text-[9px] text-slate-500">Aave overlap</span>
            </div>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="relative w-full rounded overflow-hidden bg-[#080C12]">
        {isEmpty ? (
          <div
            className="flex flex-col items-center justify-center text-slate-600"
            style={{ height: dimensions.height }}
          >
            <div className="text-2xl mb-2">◎</div>
            <p className="text-xs">Accumulating co-occurrence data…</p>
            <p className="text-[10px] text-slate-700 mt-1">
              Requires ≥2 wallets active in same pool across ≥{MIN_SHARED_WINDOWS} scan windows
            </p>
          </div>
        ) : (
          <>
            <canvas
              ref={canvasRef}
              width={dimensions.width}
              height={dimensions.height}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
              onClick={handleClick}
              className="w-full cursor-crosshair"
            />

            {/* Selected node detail panel */}
            {selectedNode && (
              <div className="absolute top-2 right-2 w-56 bg-slate-900/95 border border-slate-700 rounded-lg p-3 text-[10px] space-y-2 z-20 backdrop-blur">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 font-bold uppercase tracking-wide">Wallet Detail</span>
                  <button
                    onClick={() => { setSelectedNode(null); setSelectedWallet(null); setSelectedSignals([]); }}
                    className="text-slate-500 hover:text-slate-300 text-xs"
                  >
                    ✕
                  </button>
                </div>
                <div className="font-mono text-slate-200 break-all text-[9px]">{selectedNode.id}</div>
                <div className="space-y-1 text-slate-400">
                  <div>Type: <span className="text-slate-200">{selectedNode.agentType}</span></div>
                  {selectedNode.archetype && (
                    <div>Archetype: <span className="text-yellow-400">{selectedNode.archetype}</span></div>
                  )}
                  {selectedWallet && (
                    <>
                      <div>
                        Wash Ratio:{" "}
                        <span className={selectedWallet.wash_ratio > 10 ? "text-red-400" : "text-slate-200"}>
                          {selectedWallet.wash_ratio?.toFixed(2) ?? "—"}
                        </span>
                      </div>
                      {selectedWallet.roi_7d != null && (
                        <div>
                          ROI 7d:{" "}
                          <span className={selectedWallet.roi_7d >= 0 ? "text-green-400" : "text-red-400"}>
                            {selectedWallet.roi_7d.toFixed(1)}%
                          </span>
                        </div>
                      )}
                      {selectedWallet.smart_score != null && selectedWallet.smart_score > 0 && (
                        <div>
                          Smart Score: <span className="text-cyan-400">{selectedWallet.smart_score.toFixed(2)}</span>
                        </div>
                      )}
                      <div>Risk: <span className="text-slate-200">{selectedWallet.risk_label ?? "—"}</span></div>
                    </>
                  )}
                </div>
                {selectedSignals.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-slate-500 uppercase tracking-wide pt-1 border-t border-slate-800">
                      Pool Activity
                    </div>
                    {selectedSignals.map((sig) => (
                      <div key={sig.id} className="flex items-center justify-between gap-1">
                        <span className="text-slate-400 font-mono">
                          {sig.dex?.toUpperCase()} {sig.pool_address?.slice(0, 6)}..
                        </span>
                        <span
                          className={`font-bold ${
                            sig.alert_level === "alert" || sig.alert_level === "high_conf"
                              ? "text-red-400"
                              : sig.alert_level === "watching"
                              ? "text-yellow-400"
                              : "text-slate-500"
                          }`}
                        >
                          {sig.s_final?.toFixed(1)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                
                  <a href={`https://explorer.mantle.xyz/address/${selectedNode.id}`}
                  target="_blank" rel="noopener noreferrer" className="block text-center text-cyan-500 hover:text-cyan-300 border border-slate-700 rounded py-1 mt-1">
                  View on Explorer ↗
                </a>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer note */}
      <p className="text-[9px] text-slate-700">
        Edge weight = co-occurrence frequency ÷ pool activity size · min {MIN_SHARED_WINDOWS} shared windows to form edge · cyan glow = Aave protocol overlap detected
      </p>
    </div>
  );
}