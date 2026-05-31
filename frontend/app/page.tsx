import Link from "next/link";
import { BackendStatus } from "@/components/BackendStatus";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";

const cards = [
  {
    href: "/ticker",
    title: "Ticker analysis",
    text: "Run the FastAPI analysis service and review a clean signal, sentiment, and risk summary.",
  },
  {
    href: "/watchlist",
    title: "Watchlist scan",
    text: "Rank a small ticker universe with Meroq score, sentiment, and risk exposure.",
  },
  {
    href: "/portfolio",
    title: "Portfolio view",
    text: "Apply weights to watchlist results and inspect total exposure and downside concentration.",
  },
];

export default function Home() {
  return (
    <PageShell>
      <section className="hero product-hero">
        <p className="eyebrow">FastAPI + Next.js migration preview</p>
        <h1>Market intelligence without the notebook clutter.</h1>
        <p>
          This frontend is now a functional API client for ticker analysis, watchlist scanning, and portfolio exposure.
          Streamlit remains available while the product UI matures.
        </p>
        <div className="hero-actions">
          <Link className="primary-link" href="/ticker">
            Analyze a ticker
          </Link>
          <Link className="secondary-link" href="/watchlist">
            Scan watchlist
          </Link>
        </div>
      </section>

      <div className="grid cols-2">
        <BackendStatus />
        <section className="card">
          <p className="status-label">Local workflow</p>
          <h2>Run the API first</h2>
          <p className="muted">The frontend calls your local FastAPI backend. Keep both terminals running.</p>
          <code>python scripts/run_api.py --reload</code>
          <br />
          <br />
          <code>cd frontend && npm run dev</code>
        </section>
      </div>

      <section className="grid cols-3" style={{ marginTop: 18 }}>
        <MetricCard label="Primary backend" value="FastAPI" helper="Local API at port 8000" />
        <MetricCard label="Current production UI" value="Streamlit" helper="Still the complete app" />
        <MetricCard label="Frontend direction" value="Next.js" helper="Migration scaffold now calls real endpoints" />
      </section>

      <section className="grid cols-3" style={{ marginTop: 18 }}>
        {cards.map((card) => (
          <Link className="card interactive-card" href={card.href} key={card.href}>
            <h2>{card.title}</h2>
            <p className="muted">{card.text}</p>
          </Link>
        ))}
      </section>
    </PageShell>
  );
}
