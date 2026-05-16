export default function WhitepaperPage() {
  return (
    <div className="min-h-screen bg-[#0D1117] text-[#E6EDF3]">
      {/* ── Nav ── */}
      <nav className="border-b border-[#30363D] sticky top-0 z-50 bg-[#0D1117]/95 backdrop-blur">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2 text-[#22D3EE] font-bold text-lg hover:opacity-80 transition-opacity">
            ← MAD Dashboard
          </a>
          <span className="text-[#8B949E] text-sm">Whitepaper v2.0 · May 2026</span>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-16">

        {/* ── Cover ── */}
        <div className="mb-16">
          <div className="text-[#22D3EE] text-6xl font-black tracking-tight mb-2">MAD</div>
          <div className="text-3xl font-bold text-white mb-3">Mantle Anomaly Detector</div>
          <div className="text-xl text-[#8B949E] mb-6">On-Chain Market Integrity Infrastructure for Mantle Network</div>
          <div className="border-t border-[#30363D] pt-4 flex gap-6 text-sm text-[#8B949E]">
            <span>Version 2.0</span>
            <span>May 2026</span>
            <span>Mantle Turing Test Hackathon 2026</span>
            <a href="https://github.com/supeRIOr92/mad-mantle" target="_blank" rel="noopener" className="text-[#22D3EE] hover:underline">
              github.com/supeRIOr92/mad-mantle
            </a>
          </div>
        </div>

        {/* ── TOC ── */}
        <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-6 mb-16">
          <div className="text-[#8B949E] text-xs font-bold uppercase tracking-widest mb-4">Table of Contents</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {[
              ["1", "Executive Summary"],
              ["2", "The Problem"],
              ["3", "Market Context"],
              ["4", "Competitive Landscape"],
              ["5", "Architecture"],
              ["6", "The Detection Pipeline"],
              ["7", "Scoring Formula"],
              ["8", "Agent Intelligence Layer"],
              ["9", "Manipulation Archetypes"],
              ["10", "Alert System"],
              ["11", "Roadmap"],
              ["12", "Known Limitations"],
              ["13", "Appendix"],
            ].map(([n, title]) => (
              <a key={n} href={`#section-${n}`} className="flex gap-3 text-[#8B949E] hover:text-[#22D3EE] transition-colors py-1">
                <span className="text-[#30363D] w-4 shrink-0">{n}.</span>
                <span>{title}</span>
              </a>
            ))}
          </div>
        </div>

        {/* ── 1. Executive Summary ── */}
        <Section id="1" title="Executive Summary">
          <p className="text-[#E6EDF3] leading-7 mb-4">
            MAD scans every active liquidity pool on Mantle every 15 minutes, runs each pool through a
            three-layer detection engine, and fires an alert before the market reacts.
          </p>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            It knows not just <em>what</em> is happening — but <em>who</em> is doing it. Every wallet is
            cross-referenced against the ERC-8004 on-chain agent registry in real time. MAD distinguishes
            a legitimate market-making agent from a manipulating one. No existing surveillance tool does this.
          </p>
          <div className="grid grid-cols-3 gap-4 my-6">
            {[
              { label: "Scan interval", value: "15 min" },
              { label: "Detection layers", value: "3 (L1 · L2 · L3)" },
              { label: "Agent registry", value: "94 agents live" },
            ].map(({ label, value }) => (
              <div key={label} className="bg-[#161B22] border border-[#30363D] rounded-lg p-4 text-center">
                <div className="text-[#22D3EE] text-xl font-bold mb-1">{value}</div>
                <div className="text-[#8B949E] text-xs">{label}</div>
              </div>
            ))}
          </div>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            MAD runs on a single Railway instance, reads directly from Mantle RPC, stores signals in Supabase,
            and delivers alerts via Telegram — zero subgraph dependency, zero indexing cost.
          </p>
          <InfoCard label="WHO IT IS FOR" color="amber">
            DEX operators who need to know if their volume is real. Funds who need pre-trade market intelligence.
            Protocols who need to detect wash trading before it distorts their metrics.
            And AI agents on Mantle who need a signal layer before executing trades.
          </InfoCard>
        </Section>

        {/* ── 2. The Problem ── */}
        <Section id="2" title="The Problem">
          <p className="text-[#E6EDF3] leading-7 mb-4">
            The on-chain economy generates billions in daily volume. A significant portion of it is fabricated.
          </p>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            Wash trading — the practice of buying and selling the same asset to oneself — is trivial to execute
            in DeFi and nearly impossible to detect with conventional tools. Unlike traditional finance where such
            activity is illegal and flagged automatically, on-chain markets have no equivalent surveillance layer.
          </p>
          <p className="text-[#8B949E] text-sm mb-3">The consequences are systemic:</p>
          <BulletList items={[
            "DEX volume metrics become unreliable",
            "Liquidity routing algorithms are distorted",
            "Launchpads cannot distinguish genuine traction from coordinated inflation",
            "Funds make capital allocation decisions based on fabricated signals",
          ]} />
        </Section>

        {/* ── 3. Market Context ── */}
        <Section id="3" title="Market Context">
          <SubTitle>Why Mantle. Why Now.</SubTitle>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            Mantle is building the infrastructure layer for agent-native DeFi — a paradigm where AI agents interact
            with on-chain markets autonomously, at machine speed, 24/7. The ERC-8004 standard formalizes on-chain
            agent identity, creating a verifiable registry of autonomous participants.
          </p>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            This creates a surveillance problem that no existing tool addresses: when AI agents start dominating
            on-chain volume, traditional anomaly detection breaks down. Behavioral patterns that look suspicious
            for a human — high frequency, round amounts, sub-second execution — are entirely normal for a
            well-behaved agent. Distinguishing a legitimate market-making agent from a manipulating one requires
            a system that understands agent identity natively.
          </p>
          <p className="text-[#8B949E] text-sm mb-3">MAD was designed for this environment from the ground up. It is the only system that:</p>
          <BulletList items={[
            "Cross-references every swap against the ERC-8004 on-chain agent registry in real time",
            "Distinguishes CONFIRMED AGENT, PROBABLE AGENT, SMART MONEY, MANIPULATOR, and UNKNOWN WALLET per transaction",
            "Applies agent reputation scores as a first-class input to anomaly detection — not an afterthought",
          ]} />
          <p className="text-[#E6EDF3] leading-7 mt-4">
            The timing is deliberate. Mantle&apos;s DeFi ecosystem is in early growth — the window to establish
            baseline integrity infrastructure is now, before volume and manipulation scale together.
          </p>
        </Section>

        {/* ── 4. Competitive Landscape ── */}
        <Section id="4" title="Competitive Landscape">
          <div className="overflow-x-auto mb-6">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-[#1C2128]">
                  <th className="text-left px-4 py-3 text-[#22D3EE] border border-[#30363D]"></th>
                  {["MAD", "Chainalysis", "Nansen", "Arkham"].map(h => (
                    <th key={h} className="px-4 py-3 text-[#22D3EE] border border-[#30363D] text-center">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["Real-time (< 15 min)", "✓", "✗", "✗", "✗"],
                  ["On-chain native", "✓", "Partial", "Partial", "Partial"],
                  ["Agent identity aware", "✓", "✗", "✗", "✗"],
                  ["Mantle coverage", "✓", "✗", "Limited", "✗"],
                  ["Open source", "✓", "✗", "✗", "✗"],
                  ["Zero infra cost", "✓", "✗", "✗", "✗"],
                ].map((row, i) => (
                  <tr key={i} className="bg-[#161B22]">
                    <td className="px-4 py-3 text-[#8B949E] border border-[#30363D]">{row[0]}</td>
                    {row.slice(1).map((cell, j) => (
                      <td key={j} className={`px-4 py-3 text-center border border-[#30363D] font-mono ${cell === "✓" ? "text-[#4ADE80]" : cell === "✗" ? "text-[#F87171]" : "text-[#FBBF24]"}`}>
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            The fundamental difference: Chainalysis, Nansen, and Arkham are <strong className="text-white">retrospective</strong> intelligence tools.
            They tell you what happened. MAD is <strong className="text-[#22D3EE]">prospective</strong> — it flags anomalies as they form,
            before the alert level reaches critical.
          </p>
          <p className="text-[#E6EDF3] leading-7">
            More importantly, none of them understand agent identity. As AI agents become a larger share of
            on-chain volume, a surveillance layer that cannot distinguish human from agent is structurally blind
            to an entire class of market participants.
          </p>
        </Section>

        {/* ── 5. Architecture ── */}
        <Section id="5" title="Architecture">
          <CodeCard label="SYSTEM PIPELINE">{`Mantle RPC (rpc.mantle.xyz)
        │
        ▼
  Data Sources
  ├── Fluxion (UniV3 fork)     — eth_getLogs, PoolCreated discovery
  ├── Merchant Moe (UniV2)    — allPairs() enumeration, min-activity filter
  └── Aave v3                  — borrow/flash loan events
        │
        ▼
  Detection Engine (detector.py)
  ├── L1: Statistical
  ├── L2: Behavioral
  └── L3: Structural (async, conditional)
        │
        ▼
  Scorer (scorer.py)
  ├── Dynamic DEX weighting (DexScreener + internal validation)
  ├── Corroboration modifier
  └── Aave amplification
        │
        ▼
  Supabase  (signal_log · wallet_profile · agent_registry)
        │
        ▼
  Dashboard (real-time)  +  Telegram Alerts`}</CodeCard>
          <SubTitle className="mt-6">Design Principles</SubTitle>
          <BulletList items={[
            "Zero subgraph dependency — direct RPC queries only, no third-party indexing cost",
            "Self-validating weights — if DexScreener lacks coverage for a pool, MAD falls back to internal swap count as observability signal rather than silently zeroing the DEX",
            "Non-blocking L3 — structural analysis runs async and does not delay the primary scoring pipeline",
          ]} />
        </Section>

        {/* ── 6. Detection Pipeline ── */}
        <Section id="6" title="The Detection Pipeline">

          <LayerHeader layer="L1" title="Statistical Detection" max={60} />
          <p className="text-[#8B949E] text-sm mb-4">Measures whether current volume and transaction frequency deviate from established baseline.</p>

          <SubTitle>Z-Score — Primary Window (15 min) · max 20 pts</SubTitle>
          <FormulaCard label="FORMULA">{`z = (current_vol − μ_baseline) / σ_baseline

z ≥ 4.0  →  20 pts
z ≥ 3.0  →  15 pts
z ≥ 2.5  →  10 pts
z ≥ 2.0  →   5 pts

Baseline: 7-day rolling history, evaluated over 15-min and 1-hour windows simultaneously`}</FormulaCard>

          <SubTitle>Z-Score — Secondary Window (1h) · max 20 pts</SubTitle>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            Same formula applied to last 4 buckets (1h proxy). Catches slow-accumulation manipulation
            that evades short-window detection.
          </p>

          <SubTitle>Bollinger Band · max 20 pts</SubTitle>
          <FormulaCard label="FORMULA">{`upper_band   = μ + (σ × σ_multiplier)
breach_ratio = (current_vol − upper_band) / upper_band
pts          = min(20,  20 × breach_ratio / 0.50)

σ_multiplier = 2.0  (baseline)
             = 2.5  (adaptive — if today's range > 3× 7d avg range)`}</FormulaCard>

          <SubTitle>Poisson Deviation · max 20 pts <span className="text-[#8B949E] font-normal text-sm">(Merchant Moe pools)</span></SubTitle>
          <FormulaCard label="FORMULA">{`λ       = mean_daily_tx / 96   (96 buckets/day at 15-min intervals)
p_value = P(X ≥ current_tx | λ)

p < 0.001  →  20 pts
p < 0.010  →  15 pts
p < 0.050  →  10 pts`}</FormulaCard>

          <SubTitle>Rate-of-Change · max 20 pts <span className="text-[#8B949E] font-normal text-sm">(Merchant Moe pools)</span></SubTitle>
          <FormulaCard label="FORMULA">{`ratio = current_tx_per_bucket / avg_tx_per_bucket (7d)

ratio ≥ 5.0×   →  20 pts
ratio ≥ 3.75×  →  15 pts
ratio ≥ 2.5×   →  10 pts`}</FormulaCard>

          <div className="mt-8" />
          <LayerHeader layer="L2" title="Behavioral Analysis" max={55} />
          <p className="text-[#8B949E] text-sm mb-4">Examines who is trading and how.</p>

          <SubTitle>Wash Ratio · max 25 pts</SubTitle>
          <FormulaCard label="FORMULA">{`wash_ratio = total_volume / (|net_position_change| + ε)
             ε = 1e-9

net_position_change = Σ |wallet_net_flow| across all wallets

ratio ≥ 10×   →  25 pts (full)
ratio  5–10×  →  proportional (linear interpolation)
ratio  < 5×   →   0 pts`}</FormulaCard>
          <InfoCard label="3-WAY WASH CONFIDENCE GATE" color="red">
            <div className="space-y-1 text-sm font-mono">
              <div><span className="text-[#F87171]">HIGH_CONFIDENCE_WASH</span> — ratio &gt; 10× AND net_flow &lt; 5% AND concentration &gt; 60%</div>
              <div><span className="text-[#FBBF24]">POSSIBLE_BOT</span>         — ratio &gt; 10× AND net_flow &gt; 30% (directional = likely arbitrage)</div>
              <div><span className="text-[#8B949E]">MONITORING</span>            — elevated but not confirmed</div>
              <div><span className="text-[#4ADE80]">CLEAN</span>                 — ratio &lt; 3×</div>
            </div>
          </InfoCard>

          <SubTitle>Sender Concentration · max 15 pts</SubTitle>
          <FormulaCard label="FORMULA">{`concentration = top_5_senders_tx_count / total_tx_count

≥ 90%  →  15 pts
≥ 70%  →  10 pts
≥ 50%  →   5 pts`}</FormulaCard>

          <SubTitle>ERC-8004 Agent Reputation · max 15 pts</SubTitle>
          <FormulaCard label="FORMULA">{`high_risk_ratio = high_risk_agent_count / total_swap_count
pts             = 15 × min(high_risk_ratio, 1.0)

High risk threshold: reputation_score < 30
Registry: 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`}</FormulaCard>

          <div className="mt-8" />
          <LayerHeader layer="L3" title="Structural Forensics" max={50} async />
          <p className="text-[#E6EDF3] leading-7 mb-4">
            Only executes when L1 + L2 combined exceeds 50 pts. Runs asynchronously —
            does not delay the primary scoring pipeline.
          </p>

          <SubTitle>Benford&apos;s Law Chi-Square · max 20 pts</SubTitle>
          <FormulaCard label="FORMULA">{`expected_freq[d] = log10(1 + 1/d)   for d in {1..9}
chi2, p_value    = chisquare(observed_counts, expected_counts × n)

p < 0.05  →  pts = 20 × (1 − p_value / 0.05)

Organic transaction amounts follow Benford's Law.
Fabricated amounts deviate. Minimum 50 samples required.`}</FormulaCard>

          <SubTitle>Wallet Cycle Detection · max 30 pts</SubTitle>
          <FormulaCard label="FORMULA">{`Graph: directed, wallet → wallet edges with timestamps
Cycles: A→B→A patterns within 5–60 minute window
Max hops: 4   (NetworkX simple_cycles traversal)

pts = min(30,  10 × cycles_found)`}</FormulaCard>
        </Section>

        {/* ── 7. Scoring Formula ── */}
        <Section id="7" title="Scoring Formula">
          <FormulaCard label="PER-DEX SCORE">{`S_DEX = ((L1 + L2 + L3) / 165) × 100`}</FormulaCard>
          <FormulaCard label="MULTI-POOL AGGREGATION (outlier dampening)">{`S_DEX_agg = (top1 + top2) / 2
          = top1 × 0.7    (if top2 < 30% of top1 — outlier dampening)`}</FormulaCard>
          <FormulaCard label="CORROBORATION MODIFIER">{`flagged_dexes = count(DEX where S_DEX ≥ 40)

1 DEX  →  modifier = 1.0×  (no change)
2 DEX  →  modifier = 0.6×  (cross-DEX, reduce overcount)
3 DEX  →  modifier = 0.3×  (systemic — further dampened)

S_weighted = Σ(weight_dex × S_DEX_agg) × modifier`}</FormulaCard>
          <FormulaCard label="AAVE AMPLIFICATION (v3.0)">{`Hard gate: S_weighted < 20  →  aave_signal_effective = 0
           (Aave is a conditional amplifier, not standalone detector)

S_final = S_weighted × (1 + 0.3 × aave_signal_effective)
S_final = clamp(S_final, 0, 100)`}</FormulaCard>
          <InfoCard label="ALERT THRESHOLDS" color="red">
            <div className="space-y-2 text-sm font-mono">
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-[#F87171] shrink-0" />
                <span><strong className="text-[#F87171]">S_final ≥ 86</strong> → HIGH CONFIDENCE — verbose report + automated alert</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-[#FBBF24] shrink-0" />
                <span><strong className="text-[#FBBF24]">S_final ≥ 71</strong> → ALERT — automated alert</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-[#22D3EE] shrink-0" />
                <span><strong className="text-[#22D3EE]">S_final ≥ 41</strong> → WATCHING — scan interval escalates to 5 min</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-[#4ADE80] shrink-0" />
                <span><strong className="text-[#4ADE80]">S_final &lt; 41</strong> → CLEAR</span>
              </div>
            </div>
          </InfoCard>
        </Section>

        {/* ── 8. Agent Intelligence ── */}
        <Section id="8" title="Agent Intelligence Layer">
          <p className="text-[#E6EDF3] leading-7 mb-6">
            MAD is the only on-chain surveillance system that knows whether the entity trading is a human or
            an AI agent — and whether that agent is operating legitimately or manipulating the market.
          </p>
          <InfoCard label="ERC-8004 IDENTITY REGISTRY" color="cyan">
            <div className="space-y-1 text-sm font-mono">
              <div><span className="text-[#8B949E]">Address:</span>  0x8004A169FB4a3325136EB29fA0ceB6D2e539a432</div>
              <div><span className="text-[#8B949E]">Refresh:</span>  Every 1 hour (on-chain enumeration)</div>
              <div><span className="text-[#8B949E]">Coverage:</span> 93 registered agents as of May 2026</div>
            </div>
          </InfoCard>
          <SubTitle>Wallet Classification (priority order)</SubTitle>
          <div className="space-y-2 mb-6">
            {[
              { type: "MANIPULATOR",     color: "#F87171", desc: "(confirmed or probable) agent + wash_ratio > 10× OR cycle detected OR score ≥ 71" },
              { type: "SMART MONEY",     color: "#FBBF24", desc: "agent + ROI 7d ≥ 15% + wash_ratio ≤ 3×" },
              { type: "CONFIRMED AGENT", color: "#22D3EE", desc: "ERC-8004 registry match, no manipulation signals" },
              { type: "PROBABLE AGENT",  color: "#A78BFA", desc: "≥ 2 behavioral heuristics matched" },
              { type: "UNKNOWN WALLET",  color: "#8B949E", desc: "unclassified" },
            ].map((item, i) => (
              <div key={i} className="flex gap-3 items-start bg-[#161B22] border border-[#30363D] rounded px-4 py-3 text-sm">
                <span className="text-[#8B949E] shrink-0">{i + 1}.</span>
                <span className="font-bold shrink-0" style={{ color: item.color }}>{item.type}</span>
                <span className="text-[#8B949E]">— {item.desc}</span>
              </div>
            ))}
          </div>
          <SubTitle>Smart Money Score</SubTitle>
          <FormulaCard label="FORMULA">{`smart_score = (1 + max(roi_7d / 100, −1.0))
            × (1 − clamp(wash_ratio / 20, 0.0, 1.0))
            × (reputation_score / 100)

Range: 0.0 to ~2.0`}</FormulaCard>
          <SubTitle>Agent Behavioral Heuristics</SubTitle>
          <BulletList items={[
            "High frequency: ≥ 10 swaps per scan window",
            "Round amounts: > 50% of amounts are round numbers",
            "Fast execution: avg interval between swaps < 3 seconds",
            "Low variance: coefficient of variation (CV) < 0.10",
          ]} />
        </Section>

        {/* ── 9. Manipulation Archetypes ── */}
        <Section id="9" title="Manipulation Archetypes">
          <p className="text-[#E6EDF3] leading-7 mb-6">
            MAD classifies every flagged wallet into one of five manipulation archetypes, determined by a
            deterministic priority-order ruleset derived from behavioral signals across the scoring pipeline.
            Archetypes are assigned in real time and persisted to the wallet profile database.
          </p>
          <div className="space-y-4">
            <ArchetypeCard
              name="FLASH_WASH"
              color="#F87171"
              trigger="aave_modifier ≥ 1.5  AND  wash_ratio > 10×"
              signal="Flash loan-funded wash trading. Capital is borrowed via Aave, used to generate circular volume in a DEX pool, then repaid within the same block. The Aave amplification signal combined with high wash ratio is the definitive signature of this pattern."
            />
            <ArchetypeCard
              name="COORDINATED_WASH"
              color="#F87171"
              trigger="cycle_count ≥ 3  (NetworkX directed graph cycle detection)"
              signal="Ring-based wash trading across multiple wallets. The wallet cycle detector identifies A→B→C→A patterns within a 5–60 minute window, across up to 4 hops. Three or more detected cycles within a single scan window indicates a coordinated wash ring — not a single actor."
            />
            <ArchetypeCard
              name="PUMP_DUMP"
              color="#FBBF24"
              trigger="volume_spike_x > 15×  AND  cycle_count == 0"
              signal="Volume spike without circular flow. A >15× volume spike relative to 7d baseline, but no detected wallet cycles — indicating directional accumulation followed by distribution rather than circular wash trading."
            />
            <ArchetypeCard
              name="COMPLEX_MULTI_DEX"
              color="#A78BFA"
              trigger="corroboration == 3  (all three DEXes flagged simultaneously)"
              signal="Coordinated cross-DEX manipulation. When the same anomaly signature appears on all three monitored DEXes in the same scan window, it indicates a sophisticated actor operating across venues — either cross-venue wash trading or a coordinated market-wide manipulation campaign."
            />
            <ArchetypeCard
              name="ARB_PATTERN"
              color="#4ADE80"
              trigger="tx_per_minute > 10  AND  wash_ratio < 3×"
              signal="High-frequency trading with clean net flow. Algorithmically fast execution but directional — not circular. The wash ratio stays below the manipulation threshold, indicating genuine arbitrage or market-making activity. This archetype is surfaced for transparency, not flagged as a threat."
            />
          </div>
        </Section>

        {/* ── 10. Alert System ── */}
        <Section id="10" title="Alert System">
          <p className="text-[#E6EDF3] leading-7 mb-4">
            When MAD detects an anomaly above threshold, alerts are delivered automatically to a configured
            Telegram channel with zero latency from detection to notification.
          </p>
          <CodeCard label="ALERT WORKFLOW">{`S_final ≥ 41  →  Watch mode ON  (scan interval: 5 min)
S_final ≥ 71  →  Alert fired    →  Telegram notification sent
S_final ≥ 86  →  High Confidence alert  →  verbose report sent

S_final drops below 50 for 2 consecutive scans  →  Watch mode OFF (15 min)`}</CodeCard>
          <p className="text-[#8B949E] text-sm mt-4">
            Each alert payload includes: pool address + DEX, S_final score + alert level, detection methods triggered (which of L1/L2/L3 fired),
            top flagged wallets with agent classification and archetype, volume and corroboration data.
          </p>
        </Section>

        {/* ── 11. Roadmap ── */}
        <Section id="11" title="Roadmap">
          <SubTitle>v1.0 — Current (Live on Mantle)</SubTitle>
          <BulletList items={[
            "Real-time anomaly detection across Fluxion and Merchant Moe",
            "3-layer probabilistic scoring engine (Statistical + Behavioral + Structural)",
            "ERC-8004 agent identity integration — 93 registered agents tracked",
            "5 manipulation archetype classifiers",
            "Aave v3 flash loan amplification",
            "Live dashboard + Telegram alerts",
            "On-chain risk API (demo endpoint available)",
          ]} />

          <SubTitle className="mt-8">v2.0 — B2B API Productization</SubTitle>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            The natural evolution of MAD is an on-chain risk API — a primitive that protocols, DEXes,
            and analytics tools can integrate directly.
          </p>
          <FormulaCard label="API RESPONSE FORMAT">{`{
  "pool":         "0x509b9a...",
  "chain":        "mantle",
  "s_final":      6.4,
  "alert_level":  "none",
  "wash_probability": 0.12,
  "archetype":    "ARB_PATTERN",
  "agent_activity": {
    "confirmed_agents": 0,
    "probable_agents":  1,
    "manipulators":     0
  },
  "market_regime": {
    "active_dexes":   1,
    "confidence_cap": 0.6,
    "mode":           "low-liquidity"
  },
  "corroboration": 1,
  "timestamp":    "2026-05-12T04:43:00Z"
}`}</FormulaCard>
          <p className="text-[#8B949E] text-sm mt-3 mb-3">Target B2B consumers:</p>
          <BulletList items={[
            "DEXes — pool integrity badges, real-time wash trading flags, liquidity routing inputs",
            "Launchpads — organic demand verification before token listing",
            "On-chain funds — position risk screening, early manipulation detection",
            "Analytics platforms — raw anomaly scores as a data feed",
          ]} />

          <SubTitle className="mt-8">v3.0 — Multi-Chain Expansion (Solana)</SubTitle>
          <p className="text-[#E6EDF3] leading-7 mb-4">
            MAD&apos;s detection core — L1 Statistical, L2 Behavioral, L3 Structural — is chain-agnostic.
            The data layer is the only chain-specific component. Solana is the natural next target.
          </p>
          <BulletList items={[
            "JIT detection logic (inject-before-swap, withdraw-after-swap pattern)",
            "Sandwich attack identification",
            "Program-level instruction analysis (no EVM event topics on Solana)",
            "Yellowstone gRPC for real-time transaction streams",
          ]} />
          <InfoCard label="POSITIONING" color="amber">
            The Mantle deployment is the proof of concept. Solana is the scaled product.
          </InfoCard>
        </Section>

        {/* ── 12. Known Limitations ── */}
        <Section id="12" title="Known Limitations & Production Roadmap">
          <p className="text-[#E6EDF3] leading-7 mb-6">
            MAD v1.0 is a live system detecting real anomalies on Mantle in real time — not a prototype.
            Honest systems acknowledge their constraints. The following limitations are known, documented,
            and scheduled for resolution in v2.0.
          </p>
          <div className="space-y-4">
            <LimitationCard
              number={1}
              title="Corroboration Modifier Is Probabilistically Inverted"
              current="2 DEXes flagged → score × 0.6. 3 DEXes flagged → score × 0.3. The intent is to dampen false positives from market-wide events. The problem: cross-venue anomalies can indicate coordinated manipulation — not reduced suspicion."
              fix="Separate risk_magnitude (severity) from confidence (certainty). Corroboration should increase confidence, not decrease the score. S_final represents severity; a separate confidence field surfaces corroboration strength."
              frame="Conservative by design — biased toward avoiding false positives during the baseline-building phase. v2.0 fix."
            />
            <LimitationCard
              number={2}
              title="Outlier Dampening Thresholds Are Heuristic"
              current="if top2 < 30% of top1, apply top1 × 0.7. The 30% threshold and 0.7 discount are empirical — not statistically calibrated."
              fix="Replace with continuous smooth dampening: consensus_ratio = top2/top1; dampening = clamp(consensus_ratio, 0.4, 1.0); S = top1 × dampening. Continuous, not a hard step function."
              frame="Practically correct. Mathematically defensible only as a heuristic. Calibration against historical manipulation data is the v2.0 fix."
            />
            <LimitationCard
              number={3}
              title="Single-DEX Operating Environment Not Surfaced to API Consumers"
              current="MAD is aware that Mantle currently operates with one dominant active DEX. This context is internal — not exposed in API responses or dashboard signals."
              fix="Add market_regime field to all API responses: { active_dexes, confidence_cap, mode: 'low-liquidity' | 'normal' | 'high-activity' }. Already in v2.0 API schema."
              frame="Transparency gap, not a detection gap. MAD's scores are valid — they just need environmental context. Already addressed in v2.0 API design."
            />
            <LimitationCard
              number={4}
              title="Low-Liquidity Pool Noise Inflates Anomaly Scores"
              current="Merchant Moe UniV2 has 229 registered pairs, of which the majority are ghost pools with 0–2 swaps per scan window. A near-zero baseline means any minimal activity triggers a high Z-score — not because manipulation occurred, but because the statistical floor is too thin. This inflates Moe&apos;s s_dex contribution and can produce elevated s_final readings that do not reflect genuine anomalies."
              fix="Introduce a minimum activity filter (MIN_POOL_SWAPS) to exclude pools below a swap count threshold from Z-score computation. Only pools with statistically meaningful participation contribute to scoring. Configurable via environment variable. v2.0 fix."
              frame="MAD prioritizes statistically meaningful liquidity environments. Pools below the activity threshold are still monitored for observability — they simply do not contribute to anomaly scoring until their baseline is stable. This is consistent with how institutional surveillance systems apply minimum liquidity thresholds before treating a venue as signal-grade."
            />
          </div>
        </Section>

        {/* ── 13. Appendix ── */}
        <Section id="13" title="Appendix">
          <SubTitle>Contract Addresses (Mantle Mainnet)</SubTitle>
          <CodeCard label="ON-CHAIN REFERENCES">{`ERC-8004 Identity Registry:    0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
ERC-8004 Reputation Registry:  0x8004BAa17C55a88189AE136b182e5fdA19dE9b63
Fluxion Factory:               0xF883162Ed9c7E8EF604214c964c678E40c9B737C
Merchant Moe Factory (UniV2):  0x5bef015ca9424a7c07b68490616a4c1f094bedec
Aave v3 Pool:                  0x458F293454fE0d67EC0655f3672301301DD51422`}</CodeCard>

          <SubTitle>Infrastructure</SubTitle>
          <CodeCard label="SYSTEM SPECS">{`RPC:            https://rpc.mantle.xyz  (public, no key required)
Block time:     ~2 seconds
Scan window:    2,000 blocks (~66 minutes lookback)
Scan interval:  15 min (default)  |  5 min (watch mode, auto-escalates at S_final ≥ 70)
Chain ID:       5000`}</CodeCard>

          <SubTitle>Supabase Schema</SubTitle>
          <InfoCard label="DATABASE TABLES" color="cyan">
            <div className="space-y-1 text-sm">
              <div><span className="text-[#22D3EE] font-mono">signal_log</span>      <span className="text-[#8B949E]">— per-scan anomaly scores, alert levels, methods triggered</span></div>
              <div><span className="text-[#22D3EE] font-mono">wallet_profile</span>  <span className="text-[#8B949E]">— behavioral profiles, agent classification, archetype, smart scores</span></div>
              <div><span className="text-[#22D3EE] font-mono">agent_registry</span>  <span className="text-[#8B949E]">— ERC-8004 registered agents with reputation scores</span></div>
              <div><span className="text-[#22D3EE] font-mono">pool_baseline</span>   <span className="text-[#8B949E]">— rolling volume/tx baselines per pool</span></div>
            </div>
          </InfoCard>

          <SubTitle>Scoring Constants</SubTitle>
          <InfoCard label="CONFIGURATION" color="green">
            <div className="space-y-1 text-sm font-mono text-[#E6EDF3]">
              <div>L1 max: 60 pts  |  L2 max: 55 pts  |  L3 max: 50 pts  |  Denominator: 165</div>
              <div>WATCHING ≥ 41  |  ALERT ≥ 71  |  HIGH CONFIDENCE ≥ 86</div>
              <div>Aave alpha: 0.3  |  Aave hard gate: S_weighted &lt; 20</div>
              <div>Fallback discount: 0.5× baseline when DexScreener coverage missing</div>
              <div>DEX weights (baseline): agni=0.40  moe=0.45  fluxion=0.15</div>
            </div>
          </InfoCard>

          <SubTitle>Links</SubTitle>
          <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-4 space-y-2 text-sm font-mono">
            {[
              ["GitHub", "https://github.com/supeRIOr92/mad-mantle"],
              ["Hackathon", "https://dorahacks.io/hackathon/mantleturingtesthackathon2026"],
              ["Mantle RPC", "https://rpc.mantle.xyz"],
              ["MantleScan", "https://mantlescan.xyz"],
            ].map(([label, url]) => (
              <div key={label} className="flex gap-4">
                <span className="text-[#8B949E] w-24 shrink-0">{label}</span>
                <a href={url} target="_blank" rel="noopener" className="text-[#22D3EE] hover:underline break-all">{url}</a>
              </div>
            ))}
          </div>
        </Section>

        <div className="mt-16 pt-8 border-t border-[#30363D] text-center text-[#8B949E] text-xs">
          MAD — Mantle Anomaly Detector · Confidential · Mantle Turing Test Hackathon 2026
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={`section-${id}`} className="mb-16 scroll-mt-20">
      <div className="flex items-baseline gap-3 mb-6">
        <span className="text-[#30363D] text-2xl font-bold">{id}.</span>
        <h2 className="text-2xl font-bold text-[#22D3EE]">{title}</h2>
      </div>
      <div className="border-t border-[#30363D] pt-6">{children}</div>
    </section>
  );
}

function SubTitle({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <h3 className={`text-[#4ADE80] font-bold text-sm uppercase tracking-wide mb-3 mt-6 ${className}`}>{children}</h3>;
}

function LayerHeader({ layer, title, max, async: isAsync }: { layer: string; title: string; max: number; async?: boolean }) {
  return (
    <div className="flex items-center gap-3 mb-4 mt-2">
      <span className="bg-[#22D3EE]/10 border border-[#22D3EE]/30 text-[#22D3EE] text-xs font-bold px-2 py-1 rounded">{layer}</span>
      <span className="text-white font-bold">{title}</span>
      <span className="text-[#8B949E] text-sm">max {max} pts</span>
      {isAsync && <span className="bg-[#A78BFA]/10 border border-[#A78BFA]/30 text-[#A78BFA] text-xs px-2 py-1 rounded">async</span>}
    </div>
  );
}

function CodeCard({ label, children }: { label: string; children: string }) {
  return (
    <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-4 mb-4">
      <div className="text-[#FBBF24] text-xs font-bold uppercase tracking-widest mb-3">{label}</div>
      <pre className="text-[#79C0FF] text-xs font-mono leading-5 whitespace-pre overflow-x-auto">{children}</pre>
    </div>
  );
}

function FormulaCard({ label, children }: { label: string; children: string }) {
  return (
    <div className="bg-[#161B22] border border-[#22D3EE]/30 rounded-lg p-4 mb-4">
      <div className="text-[#22D3EE] text-xs font-bold uppercase tracking-widest mb-3">{label}</div>
      <pre className="text-[#79C0FF] text-xs font-mono leading-5 whitespace-pre overflow-x-auto">{children}</pre>
    </div>
  );
}

function InfoCard({ label, color, children }: { label: string; color: "amber" | "red" | "cyan" | "green"; children: React.ReactNode }) {
  const colors = {
    amber: { border: "border-[#FBBF24]/30", label: "text-[#FBBF24]" },
    red:   { border: "border-[#F87171]/30", label: "text-[#F87171]" },
    cyan:  { border: "border-[#22D3EE]/30", label: "text-[#22D3EE]" },
    green: { border: "border-[#4ADE80]/30", label: "text-[#4ADE80]" },
  };
  return (
    <div className={`bg-[#161B22] border ${colors[color].border} rounded-lg p-4 mb-4`}>
      <div className={`${colors[color].label} text-xs font-bold uppercase tracking-widest mb-3`}>{label}</div>
      <div className="text-[#E6EDF3] text-sm leading-6">{children}</div>
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2 mb-4">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 text-sm text-[#E6EDF3] leading-6">
          <span className="text-[#22D3EE] mt-1 shrink-0">›</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function ArchetypeCard({ name, color, trigger, signal }: { name: string; color: string; trigger: string; signal: string }) {
  return (
    <div className="bg-[#161B22] rounded-lg p-5" style={{ borderLeft: `3px solid ${color}`, border: `1px solid #30363D`, borderLeftColor: color }}>
      <div className="font-bold text-base mb-3" style={{ color }}>{name}</div>
      <div className="mb-3">
        <div className="text-[#8B949E] text-xs uppercase tracking-widest font-bold mb-1">Trigger Conditions</div>
        <code className="text-[#79C0FF] text-xs font-mono">{trigger}</code>
      </div>
      <div>
        <div className="text-[#8B949E] text-xs uppercase tracking-widest font-bold mb-1">Manipulation Signal</div>
        <p className="text-[#E6EDF3] text-sm leading-6">{signal}</p>
      </div>
    </div>
  );
}

function LimitationCard({ number, title, current, fix, frame }: {
  number: number; title: string; current: string; fix: string; frame: string;
}) {
  return (
    <div className="bg-[#161B22] border border-[#F87171]/30 rounded-lg p-5">
      <div className="text-[#F87171] text-xs font-bold uppercase tracking-widest mb-1">WEAK SPOT #{number}</div>
      <div className="text-white font-bold mb-4">{title}</div>
      <div className="space-y-3 text-sm">
        <div>
          <div className="text-[#8B949E] text-xs uppercase tracking-widest font-bold mb-1">Current Behavior</div>
          <p className="text-[#E6EDF3] leading-6">{current}</p>
        </div>
        <div>
          <div className="text-[#4ADE80] text-xs uppercase tracking-widest font-bold mb-1">v2.0 Fix</div>
          <p className="text-[#E6EDF3] leading-6">{fix}</p>
        </div>
        <div>
          <div className="text-[#8B949E] text-xs uppercase tracking-widest font-bold mb-1">Framing</div>
          <p className="text-[#8B949E] leading-6 italic">{frame}</p>
        </div>
      </div>
    </div>
  );
}
