"use client";

import { useEffect, useState } from "react";
import { API_BASE, getHealth } from "@/lib/api";

type Status = "checking" | "online" | "offline";

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [message, setMessage] = useState("Checking FastAPI backend...");

  useEffect(() => {
    getHealth()
      .then((body) => {
        setStatus("online");
        setMessage(`Connected to ${body.app ?? "Meroq API"} ${body.version ?? ""}`);
      })
      .catch((error: Error) => {
        setStatus("offline");
        setMessage(error.message);
      });
  }, []);

  return (
    <section className={`status-card ${status}`}>
      <p className="status-label">Backend status</p>
      <h2>{status === "online" ? "Connected" : status === "offline" ? "Not connected" : "Checking"}</h2>
      <p>{message}</p>
      <code>{API_BASE}</code>
    </section>
  );
}
