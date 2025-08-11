import React, { useEffect, useMemo, useState } from "react";

type Point = { ts: string; value: number };

export function MetricsChart() {
  const [series, setSeries] = useState<Record<string, Point[]>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [compare, setCompare] = useState<Record<string, { chunks: number[]; delta: number }>>({});
  useEffect(() => {
    async function fetchData() {
      const res = await fetch("/analytics/metrics");
      const json = (await res.json()) as Record<string, Point[]>;
      setSeries(json);
      const cmp = await fetch("/analytics/metrics/compare?n=5").then((r) => r.json());
      setCompare(cmp as Record<string, { chunks: number[]; delta: number }>);
    }
    fetchData();
    const id = setInterval(fetchData, 2000);
    return () => clearInterval(id);
  }, []);

  const keys = useMemo(() => Object.keys(series).sort(), [series]);

  return (
    <div className="card">
      <h2>Metrics</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        {keys.map((k) => (
          <label
            key={k}
            style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
            <input
              type="radio"
              name="metric"
              checked={selected === k}
              onChange={() => setSelected(k)}
            />
            {k}
          </label>
        ))}
        {selected && (
          <button
            onClick={() => setSelected(null)}
            style={{ marginLeft: 8 }}>
            Show all
          </button>
        )}
      </div>
      {selected ? (
        <div>
          <MiniChart
            name={selected}
            points={series[selected] ?? []}
          />
          {compare[selected] && (
            <div style={{ marginTop: 6, fontSize: 12, color: "#6b7280" }}>
              Chunks avg: {compare[selected].chunks.map((v) => v.toFixed(2)).join(", ")} | Delta: {compare[selected].delta.toFixed(2)}
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
          {keys.map((name) => (
            <MiniChart
              key={name}
              name={name}
              points={series[name] ?? []}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MiniChart({ name, points }: { name: string; points: Point[] }) {
  const last = points.at(-1)?.value;
  return (
    <div className="mini-chart card">
      <div className="header">
        <strong>{name}</strong>
        <span className="delta">{last !== undefined ? last.toFixed(2) : "-"}</span>
      </div>
      <div className="bars">
        {points.slice(-80).map((p, i) => (
          <div
            key={i}
            className="bar"
            title={`${p.ts}: ${p.value}`}
            style={{ height: Math.max(2, p.value * 10) }}
          />
        ))}
      </div>
    </div>
  );
}
