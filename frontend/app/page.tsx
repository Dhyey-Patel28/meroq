import Link from "next/link";
import { BackendStatus } from "@/components/BackendStatus";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";

const cards = [
  {
    href: "/ticker",
    title: "Ticker analysis",
    text: "Get a concise signal, risk lens, and recent source-linked headlines for one company.",
  },
  {
    href: "/watchlist",
    title: "Watchlist scan",
    text: "Rank a small universe by Meroq score, sentiment, and downside-risk exposure.",
  },
  {
    href: "/portfolio",
    title: "Portfolio view",
    text: "Apply weights to understand where score, risk, and exposure are concentrated.",
  },
];

export default function Home() {
  return (
    <PageShell>
      <section className="hero product-hero product-hero-split">
        <div>
          <p className="eyebrow">Local market intelligence</p>
          <h1>Evidence-first stock analysis for people, not notebooks.</h1>
          <p>
            Meroq connects a local FastAPI analysis engine to a cleaner product interface. Start with
            the signal, then inspect the model, risk lens, and source articles behind it.
          </p>
          <div className="hero-actions">
            <Link className="primary-link" href="/ticker">
              Analyze a ticker
            </Link>
            <Link className="secondary-link" href="/watchlist">
              Scan watchlist
            </Link>
          </div>
        </div>
        <div className="hero-mini-card">
          <span>Current focus</span>
          <strong>Human-centered UX with transparent source links</strong>
          <p>Streamlit remains available for deep research while this frontend matures into the product UI.</p>
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

      <section className="grid cols-4" style={{ marginTop: 18 }}>
        <MetricCard label="Backend" value="FastAPI" helper="Local API at port 8000" />
        <MetricCard label="Research UI" value="Streamlit" helper="Complete analysis surface" />
        <MetricCard label="Product UI" value="Next.js" helper="Clean workflow for users" />
        <MetricCard label="Trust layer" value="Source links" helper="Open original articles" />
      </section>

      <section className="grid cols-3" style={{ marginTop: 18 }}>
        {cards.map((card) => (
          <Link className="card interactive-card" href={card.href} key={card.href}>
            <h2>{card.title}</h2>
            <p className="muted">{card.text}</p>
          </Link>
        ))}
      </section>

      <section className="card subtle-card" style={{ marginTop: 18 }}>
        <p className="status-label">Design principle</p>
        <h2>Show the conclusion, then the receipts.</h2>
        <p className="muted">
          Meroq should be understandable before it is technical. Every signal should make it clear what the system thinks,
          how confident it is, and which source material influenced the result.
        </p>
      </section>
    </PageShell>
  );
}
