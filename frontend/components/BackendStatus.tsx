"use client";

import { useEffect, useState } from "react";
import { API_BASE, getHealth, type HealthResponse } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";

type Status = "checking" | "online" | "offline";

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [message, setMessage] = useState("Checking FastAPI backend...");

  useEffect(() => {
    getHealth()
      .then((body) => {
        setStatus("online");
        setHealth(body);
        setMessage(`Connected to ${body.app ?? "Meroq API"} ${body.version ?? ""}`);
      })
      .catch((error: Error) => {
        setStatus("offline");
        setMessage(error.message);
      });
  }, []);

  const tone = status === "online" ? "positive" : status === "offline" ? "negative" : "warning";

  return (
    <section className={`status-card ${status}`}>
      <div className="card-heading-row">
        <p className="status-label">Backend status</p>
        <StatusPill label={status === "online" ? "Online" : status === "offline" ? "Offline" : "Checking"} tone={tone} />
      </div>
      <h2>{status === "online" ? "Connected" : status === "offline" ? "Start the API" : "Checking"}</h2>
      <p>{message}</p>
      <code>{API_BASE}</code>
      {health?.generated_at_utc ? <p className="muted small">Last check: {health.generated_at_utc}</p> : null}
    </section>
  );
}
