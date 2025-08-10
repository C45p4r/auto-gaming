import React, { useEffect, useMemo, useRef, useState } from "react";
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
  const [guidance, setGuidance] = useState<{ prioritize: string[]; avoid: string[] }>({ prioritize: [], avoid: [] });
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
        </div>
      </section>
      <section>
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
      <section>
        <h2>Status</h2>
        <div>Agent: {status.agent_state ?? "-"}</div>
        <div>Task: {status.task ?? "-"}</div>
        <div>Confidence: {status.confidence ?? "-"}</div>
        <div>Next: {status.next ?? "-"}</div>
      </section>
      <section>
        <h2>Performance</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
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
      <section>
        <h2>Client Logs</h2>
        <div style={{ maxHeight: 180, overflow: "auto", background: "#111", color: "#0f0", padding: 8, fontFamily: "Consolas, monospace", fontSize: 12 }}>
          {log.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      </section>
      <section>
        <h2>Window</h2>
        <WindowControls />
      </section>
      <section>
        <h2>Guidance</h2>
        <div>Prioritize: {guidance.prioritize.join(", ") || "-"}</div>
        <div>Avoid: {guidance.avoid.join(", ") || "-"}</div>
      </section>
      <section>
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
      <section>
        <MetricsChart />
      </section>
      <section>
        <h2>Memory</h2>
        <MemoryPanel />
      </section>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);

function Stat(props: { label: string; value: string | number }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 8 }}>
      <div style={{ color: "#6b7280", fontSize: 12 }}>{props.label}</div>
      <div style={{ fontSize: 18, fontWeight: 600 }}>{props.value}</div>
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
