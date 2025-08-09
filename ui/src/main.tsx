import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

type TelemetryMsg = { type: "status"; data: { task: string | null; confidence: number | null; next: string | null } } | { type: "decision"; data: any } | { type: "guidance"; data: { prioritize: string[]; avoid: string[] } };

function App() {
  const [status, setStatus] = useState<{ task: string | null; confidence: number | null; next: string | null }>({ task: null, confidence: null, next: null });
  const [decisions, setDecisions] = useState<any[]>([]);
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
    };
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  return (
    <div style={{ fontFamily: "Inter, system-ui, Arial", padding: 16, maxWidth: 960, margin: "0 auto" }}>
      <h1>auto-gaming</h1>
      <section>
        <h2>Status</h2>
        <div>Task: {status.task ?? "-"}</div>
        <div>Confidence: {status.confidence ?? "-"}</div>
        <div>Next: {status.next ?? "-"}</div>
      </section>
      <section>
        <h2>Guidance</h2>
        <div>Prioritize: {guidance.prioritize.join(", ") || "-"}</div>
        <div>Avoid: {guidance.avoid.join(", ") || "-"}</div>
      </section>
      <section>
        <h2>Decisions</h2>
        <ul>
          {decisions.map((d, idx) => (
            <li key={idx}>
              <code>{d.timestamp_utc}</code> — {d.reason}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
