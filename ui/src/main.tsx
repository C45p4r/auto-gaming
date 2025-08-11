import React, { useEffect, useMemo, useRef, useState } from "react";
import "./styles.scss";
import { MetricsChart } from "./components/Charts";
import { createRoot } from "react-dom/client";

type StatusPayload = {
  agent_state?: string | null;
  task: string | null;
  confidence: number | null;
  next: string | null;
  fps?: number;
  actions?: number;
  taps?: number;
  swipes?: number;
  backs?: number;
  blocks?: number;
  stuck_events?: number;
  window_ok?: number;
  capture_backend?: string;
  input_backend?: string;
  model_policy?: string;
  model_id_policy?: string;
};
type TelemetryMsg = { type: "status"; data: StatusPayload } | { type: "decision"; data: any } | { type: "guidance"; data: { prioritize: string[]; avoid: string[] } } | { type: "step"; data: { timestamp_utc: string; kind: string; payload: any } };

function App() {
  const [status, setStatus] = useState<StatusPayload>({ agent_state: null, task: null, confidence: null, next: null });
  const [log, setLog] = useState<string[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [steps, setSteps] = useState<{ timestamp_utc: string; kind: string; payload: any }[]>([]);
  const [guidance, setGuidance] = useState<{ prioritize: string[]; avoid: string[]; help_prompt?: string }>({ prioritize: [], avoid: [], help_prompt: "" });
  const [hfEnabled, setHfEnabled] = useState<boolean>(true);
  const [theme, setTheme] = useState<string>(() => {
    try {
      return localStorage.getItem("ui_theme") || "light";
    } catch {
      return "light";
    }
  });
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = (location.protocol === "https:" ? "wss://" : "ws://") + location.host.replace(/:\d+$/, ":8000") + "/telemetry/ws";
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (evt) => {
      const msg: TelemetryMsg = JSON.parse(evt.data);
      if (msg.type === "status") setStatus(msg.data);
      if (msg.type === "decision") setDecisions((d) => [msg.data, ...d].slice(0, 200));
      if (msg.type === "guidance") setGuidance(msg.data);
      if (msg.type === "step") setSteps((s) => [msg.data, ...s].slice(0, 200));
      setLog((l) => [new Date().toLocaleTimeString() + " " + (typeof msg === "string" ? msg : JSON.stringify(msg)), ...l].slice(0, 200));
    };
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("ui_theme", theme);
    } catch {}
    const root = document.documentElement;
    if (theme === "dark") {
      root.style.backgroundColor = "#0f172a";
      root.style.color = "#e5e7eb";
    } else if (theme === "light") {
      root.style.backgroundColor = "#ffffff";
      root.style.color = "#111827";
    } else {
      root.style.backgroundColor = "";
      root.style.color = "";
    }
  }, [theme]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      const k = e.key.toLowerCase();
      if (k === "s") fetch("/telemetry/control/start", { method: "POST" });
      if (k === "p") fetch("/telemetry/control/pause", { method: "POST" });
      if (k === "x") fetch("/telemetry/control/stop", { method: "POST" });
      if (k === "b") fetch("/telemetry/control/act", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type: "back" }) });
      if (k === "w") fetch("/telemetry/control/act", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type: "wait", seconds: 1.0 }) });
      if (k === "g") fetch("/telemetry/control/act", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type: "swipe_gentle" }) });
      if (k === "t") setTheme((prev) => (prev === "light" ? "dark" : "light"));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div style={{ fontFamily: "Inter, system-ui, Arial", padding: 16, maxWidth: 960, margin: "0 auto" }}>
      <h1>auto-gaming</h1>
      <section style={{ position: "sticky", top: 0, background: "#fff", paddingBottom: 8, zIndex: 10 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => fetch("/telemetry/control/start", { method: "POST" })}
            style={{ padding: "6px 12px", background: "#10b981", color: "#fff", borderRadius: 6, border: 0 }}>
            Start
          </button>
          <button
            onClick={() => fetch("/telemetry/control/pause", { method: "POST" })}
            style={{ padding: "6px 12px", background: "#f59e0b", color: "#fff", borderRadius: 6, border: 0 }}>
            Pause
          </button>
          <button
            onClick={() => fetch("/telemetry/control/stop", { method: "POST" })}
            style={{ padding: "6px 12px", background: "#ef4444", color: "#fff", borderRadius: 6, border: 0 }}>
            Stop
          </button>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <label>
              Theme
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                style={{ marginLeft: 6 }}>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System</option>
              </select>
            </label>
            <span style={{ fontSize: 12, color: "#6b7280" }}>(Shortcuts: S start, P pause, X stop, B back, W wait, G gentle swipe, T theme)</span>
          </div>
        </div>
      </section>
      <section className="card">
        <h2>Agent Steps</h2>
        <ul>
          {steps.map((s, idx) => (
            <li key={idx}>
              <code>{s.timestamp_utc}</code> — <strong>{s.kind}</strong>
              <pre style={{ whiteSpace: "pre-wrap", overflow: "auto", background: "#f9fafb", padding: 8 }}>{JSON.stringify(s.payload, null, 2)}</pre>
            </li>
          ))}
        </ul>
      </section>
      <section className="card">
        <h2>Status</h2>
        <div>Agent: {status.agent_state ?? "-"}</div>
        <div>Task: {status.task ?? "-"}</div>
        <div>Confidence: {status.confidence ?? "-"}</div>
        <div>Next: {status.next ?? "-"}</div>
        <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={() => fetch("/telemetry/control/act", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type: "back" }) })}>Back</button>
          <button onClick={() => fetch("/telemetry/control/act", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type: "wait", seconds: 1.0 }) })}>Wait 1s</button>
          <button onClick={() => fetch("/telemetry/control/act", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type: "swipe_gentle" }) })}>Swipe gentle</button>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <input
              type="checkbox"
              checked={hfEnabled}
              onChange={async (e) => {
                setHfEnabled(e.target.checked);
                await fetch("/telemetry/control/model/policy", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: e.target.checked }) });
              }}
            />
            hf-policy enabled
          </label>
        </div>
      </section>
      <section className="card">
        <h2>Performance</h2>
        <div className="grid-3">
          <Stat
            label="FPS"
            value={status.fps !== undefined ? status.fps.toFixed(2) : "-"}
          />
          <Stat
            label="Actions"
            value={status.actions ?? 0}
          />
          <Stat
            label="Taps"
            value={status.taps ?? 0}
          />
          <Stat
            label="Swipes"
            value={status.swipes ?? 0}
          />
          <Stat
            label="Backs"
            value={status.backs ?? 0}
          />
          <Stat
            label="Blocks"
            value={status.blocks ?? 0}
          />
          <Stat
            label="Stuck"
            value={status.stuck_events ?? 0}
          />
          <Stat
            label="Window OK"
            value={status.window_ok ? "Yes" : "No"}
          />
          <Stat
            label="Capture"
            value={status.capture_backend ?? "-"}
          />
          <Stat
            label="Input"
            value={status.input_backend ?? "-"}
          />
        </div>
        <div style={{ marginTop: 6, color: "#6b7280", fontSize: 12 }}>
          Model: {status.model_policy} {status.model_id_policy}
        </div>
      </section>
      <section className="card">
        <h2>Client Logs</h2>
        <div style={{ maxHeight: 180, overflow: "auto", background: "#111", color: "#0f0", padding: 8, fontFamily: "Consolas, monospace", fontSize: 12 }}>
          {log.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      </section>
      <section className="card">
        <h2>Window</h2>
        <WindowControls />
      </section>
      <section className="card">
        <h2>Doctor</h2>
        <DoctorPanel />
      </section>
      <section className="card">
        <h2>Guidance</h2>
        <div>Prioritize: {guidance.prioritize.join(", ") || "-"}</div>
        <div>Avoid: {guidance.avoid.join(", ") || "-"}</div>
        <HelpPromptBox current={guidance.help_prompt || ""} />
        <GuidanceEditor
          current={guidance}
          onSaved={() => {
            /* no-op: ws will update */
          }}
        />
      </section>
      <section className="card">
        <h2>Suggestions</h2>
        <SuggestionBox suggestions={((guidance as any).suggestions as string[]) || []} />
      </section>
      <section className="card">
        <h2>Decisions</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Time</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Who</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Action</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Latency (ms)</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>OCR</th>
            </tr>
          </thead>
          <tbody>
            {decisions.map((d, idx) => (
              <tr key={idx}>
                <td style={{ padding: "6px 4px" }}>
                  <code>{d.timestamp_utc}</code>
                </td>
                <td style={{ padding: "6px 4px" }}>{d.who}</td>
                <td style={{ padding: "6px 4px" }}>{d.action?.type}</td>
                <td style={{ padding: "6px 4px" }}>{typeof d.latency_ms === "number" ? d.latency_ms.toFixed(1) : "-"}</td>
                <td style={{ padding: "6px 4px", maxWidth: 260, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{d.ocr_fp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card">
        <h2>Session Replay</h2>
        <SessionReplay />
      </section>
      <section className="card">
        <MetricsChart />
      </section>
      <section className="card">
        <h2>Memory</h2>
        <MemoryPanel />
      </section>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);

function Stat(props: { label: string; value: string | number }) {
  return (
    <div className="stat-tile">
      <div className="stat-label">{props.label}</div>
      <div className="stat-value">{props.value}</div>
    </div>
  );
}

function MemoryPanel() {
  const [items, setItems] = useState<{ ts: string; image_url: string; ocr?: string }[]>([]);
  async function refresh() {
    const j = await fetch("/telemetry/memory/recent").then((r) => r.json());
    setItems(j);
  }
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
      {items.map((m) => (
        <div
          key={m.ts}
          style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 8 }}>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
            <code>{m.ts}</code>
          </div>
          <div style={{ width: "100%", aspectRatio: "16 / 9", overflow: "hidden", background: "#000" }}>
            <img
              src={m.image_url}
              alt={m.ts}
              style={{ width: "100%" }}
            />
          </div>
          {m.ocr && (
            <div style={{ marginTop: 6 }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>OCR</div>
              <div style={{ fontSize: 12, whiteSpace: "pre-wrap" }}>{m.ocr.slice(0, 400)}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function SessionReplay() {
  const [rows, setRows] = useState<{ ts: string; action: string; reason: string; image_path?: string | null }[]>([]);
  const [jsonl, setJsonl] = useState<string>("");
  const [idx, setIdx] = useState<number>(-1);
  async function refresh() {
    const j = await fetch("/analytics/session").then((r) => r.json());
    setRows(j);
    if (j.length && idx === -1) setIdx(j.length - 1);
  }
  async function exportJsonl() {
    const t = await fetch("/analytics/session/export").then((r) => r.text());
    setJsonl(t);
  }
  async function importJsonl() {
    await fetch("/analytics/session/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ jsonl }) });
    await refresh();
  }
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);
  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
        <button onClick={exportJsonl}>Export</button>
        <button onClick={importJsonl}>Import</button>
        <textarea
          placeholder="paste JSONL here"
          value={jsonl}
          onChange={(e) => setJsonl(e.target.value)}
          style={{ flex: 1, height: 80 }}
        />
      </div>
      {rows.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <input
            type="range"
            min={0}
            max={rows.length - 1}
            value={Math.max(0, Math.min(idx, rows.length - 1))}
            onChange={(e) => setIdx(Number(e.target.value))}
            style={{ width: "100%" }}
          />
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            Index: {idx} / {rows.length - 1}
          </div>
          {rows[idx] && (
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginTop: 6 }}>
              <div>
                <div>
                  <strong>{rows[idx].ts}</strong>
                </div>
                <div>Action: {rows[idx].action}</div>
                <div>Reason: {rows[idx].reason}</div>
              </div>
              <div style={{ width: 240, background: "#000" }}>
                {rows[idx].image_path ? (
                  <img
                    src={rows[idx].image_path}
                    alt={rows[idx].ts}
                    style={{ width: "100%" }}
                  />
                ) : (
                  <div style={{ color: "#9ca3af", padding: 8 }}>(no frame)</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Time</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Action</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Reason</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>Frame</th>
          </tr>
        </thead>
        <tbody>
          {rows
            .slice(-100)
            .reverse()
            .map((r, i) => (
              <tr key={i}>
                <td style={{ padding: 6 }}>
                  <code>{r.ts}</code>
                </td>
                <td style={{ padding: 6 }}>{r.action}</td>
                <td style={{ padding: 6 }}>{r.reason}</td>
                <td style={{ padding: 6 }}>
                  {r.image_path ? (
                    <a
                      href={r.image_path}
                      target="_blank">
                      view
                    </a>
                  ) : (
                    "-"
                  )}
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}

function WindowControls() {
  const [rect, setRect] = useState<{ left: number; top: number; width: number; height: number } | null>(null);
  async function refresh() {
    const j = await fetch("/telemetry/window/rect").then((r) => r.json());
    setRect(j);
  }
  async function apply() {
    if (!rect) return;
    await fetch("/telemetry/window/set", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rect),
    });
    await refresh();
  }
  useEffect(() => {
    refresh();
  }, []);
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <button
        onClick={refresh}
        style={{ padding: "6px 12px" }}>
        Refresh
      </button>
      <label>
        Left
        <input
          type="number"
          value={rect?.left ?? 0}
          onChange={(e) => setRect({ ...(rect ?? { left: 0, top: 0, width: 1280, height: 720 }), left: Number(e.target.value) })}
          style={{ width: 90, marginLeft: 6 }}
        />
      </label>
      <label>
        Top
        <input
          type="number"
          value={rect?.top ?? 0}
          onChange={(e) => setRect({ ...(rect ?? { left: 0, top: 0, width: 1280, height: 720 }), top: Number(e.target.value) })}
          style={{ width: 90, marginLeft: 6 }}
        />
      </label>
      <label>
        Width
        <input
          type="number"
          value={rect?.width ?? 1280}
          onChange={(e) => setRect({ ...(rect ?? { left: 0, top: 0, width: 1280, height: 720 }), width: Number(e.target.value) })}
          style={{ width: 90, marginLeft: 6 }}
        />
      </label>
      <label>
        Height
        <input
          type="number"
          value={rect?.height ?? 720}
          onChange={(e) => setRect({ ...(rect ?? { left: 0, top: 0, width: 1280, height: 720 }), height: Number(e.target.value) })}
          style={{ width: 90, marginLeft: 6 }}
        />
      </label>
      <button
        onClick={apply}
        style={{ padding: "6px 12px" }}>
        Apply
      </button>
    </div>
  );
}

function DoctorPanel() {
  const [data, setData] = useState<{ ok: boolean; issues: string[]; details: Record<string, any>; suggestions?: { issue: string; suggestion: string }[] } | null>(null);
  async function refresh() {
    const j = await fetch("/telemetry/doctor/self-check").then((r) => r.json());
    setData(j);
  }
  useEffect(() => {
    refresh();
  }, []);
  if (!data) return null;
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 8 }}>
      <div>Status: {data.ok ? "OK" : "Issues"}</div>
      {!data.ok && (
        <ul>
          {data.issues.map((x, i) => (
            <li
              key={i}
              style={{ color: "#b91c1c" }}>
              {x}
            </li>
          ))}
        </ul>
      )}
      {data.suggestions && data.suggestions.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontWeight: 600 }}>Suggestions</div>
          <ul>
            {data.suggestions.map((s, i) => (
              <li key={i}>
                <strong>{s.issue}:</strong> {s.suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}
      <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(data.details, null, 2)}</pre>
      <button
        onClick={refresh}
        style={{ padding: "6px 12px" }}>
        Re-run
      </button>
    </div>
  );
}

function GuidanceEditor({ current, onSaved }: { current: { prioritize: string[]; avoid: string[] }; onSaved: () => void }) {
  const [pri, setPri] = useState<string>(current.prioritize.join(", "));
  const [avd, setAvd] = useState<string>(current.avoid.join(", "));
  async function save() {
    const payload = {
      prioritize: pri
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      avoid: avd
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    await fetch("/telemetry/guidance", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    onSaved();
  }
  return (
    <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ fontWeight: 600 }}>Edit Guidance</div>
      <label>
        Prioritize
        <input
          value={pri}
          onChange={(e) => setPri(e.target.value)}
          placeholder="comma separated"
          style={{ marginLeft: 6, width: "100%" }}
        />
      </label>
      <label>
        Avoid
        <input
          value={avd}
          onChange={(e) => setAvd(e.target.value)}
          placeholder="comma separated"
          style={{ marginLeft: 6, width: "100%" }}
        />
      </label>
      <div>
        <button onClick={save}>Save</button>
      </div>
    </div>
  );
}

function SuggestionBox({ suggestions }: { suggestions: string[] }) {
  const [text, setText] = useState("");
  async function submit() {
    const t = text.trim();
    if (!t) return;
    await fetch("/telemetry/guidance/suggest", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: t }) });
    setText("");
  }
  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Suggest goals, strategies, or hints (won't pause the agent)" style={{ flex: 1, height: 60 }} />
        <button onClick={submit}>Submit</button>
      </div>
      {suggestions && suggestions.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, color: "#6b7280" }}>Recent Suggestions</div>
          <ul>
            {[...suggestions].slice(-10).reverse().map((s, i) => (
              <li key={i} style={{ fontSize: 12 }}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function HelpPromptBox({ current }: { current: string }) {
  const [text, setText] = useState<string>(current || "");
  async function save() {
    await fetch("/telemetry/guidance/help", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
  }
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontWeight: 600 }}>Need help? Describe the screen/problem:</div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g., I am at battle menu, how to proceed?"
        style={{ width: "100%", height: 60 }}
      />
      <div>
        <button onClick={save}>Submit</button>
      </div>
    </div>
  );
}
