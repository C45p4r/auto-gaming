import React, { useEffect, useState } from "react";

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
    const id = setInterval(fetchData, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <h2>Metrics</h2>
      {Object.entries(series).map(([name, points]) => (
        <div key={name} style={{ marginBottom: 12 }}>
          <strong>{name}</strong>
          <div style={{ display: "flex", gap: 4, alignItems: "flex-end", minHeight: 60 }}>
            {points.slice(-50).map((p, i) => (
              <div key={i} title={`${p.ts}: ${p.value}`} style={{ width: 4, height: Math.max(2, p.value * 10), background: "#4f46e5" }} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
