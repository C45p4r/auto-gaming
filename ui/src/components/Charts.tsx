import React, { useEffect, useMemo, useState } from "react";

type Point = { ts: string; value: number };

export function MetricsChart() {
  const [series, setSeries] = useState<Record<string, Point[]>>({});
  useEffect(() => {
    async function fetchData() {
      const res = await fetch("/analytics/metrics");
      const json = (await res.json()) as Record<string, Point[]>;
      setSeries(json);
    }
    fetchData();
    const id = setInterval(fetchData, 2000);
    return () => clearInterval(id);
  }, []);

  const keys = useMemo(() => Object.keys(series).sort(), [series]);

  return (
    <div>
      <h2>Metrics</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
        {keys.map((name) => (
          <MiniChart
            key={name}
            name={name}
            points={series[name] ?? []}
          />
        ))}
      </div>
    </div>
  );
}

function MiniChart({ name, points }: { name: string; points: Point[] }) {
  const last = points.at(-1)?.value;
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <strong>{name}</strong>
        <span style={{ color: "#6b7280" }}>{last !== undefined ? last.toFixed(2) : "-"}</span>
      </div>
      <div style={{ display: "flex", gap: 2, alignItems: "flex-end", minHeight: 60 }}>
        {points.slice(-80).map((p, i) => (
          <div
            key={i}
            title={`${p.ts}: ${p.value}`}
            style={{ width: 3, height: Math.max(2, p.value * 10), background: "#4f46e5" }}
          />
        ))}
      </div>
    </div>
  );
}
