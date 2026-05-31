import Link from "next/link";
import { BackendStatus } from "@/components/BackendStatus";
import { PageShell } from "@/components/PageShell";

const cards = [
  {
    href: "/ticker",
    title: "Ticker analysis",
    text: "Call the FastAPI ticker endpoint and display the latest signal, sentiment, and risk summary.",
  },
  {
    href: "/watchlist",
    title: "Watchlist scan",
    text: "Scan a small ticker universe and rank names with the Meroq score.",
  },
  {
    href: "/portfolio",
    title: "Portfolio view",
    text: "Combine watchlist scan results with weights to inspect risk and exposure.",
  },
];

export default function Home() {
  return (
    <PageShell>
      <section className="hero">
        <h1>Meroq frontend scaffold</h1>
        <p>
          A lightweight Next.js shell for the Meroq FastAPI backend. Streamlit remains the main UI while this
          frontend stabilizes the future product direction.
        </p>
      </section>

      <div className="grid cols-2">
        <BackendStatus />
        <section className="card">
          <h2>How to run</h2>
          <p className="muted">Start the API first, then run the frontend development server.</p>
          <code>python scripts/run_api.py --reload</code>
          <br />
          <br />
          <code>cd frontend && npm install && npm run dev</code>
        </section>
      </div>

      <section className="grid cols-3" style={{ marginTop: 18 }}>
        {cards.map((card) => (
          <Link className="card" href={card.href} key={card.href}>
            <h2>{card.title}</h2>
            <p className="muted">{card.text}</p>
          </Link>
        ))}
      </section>
    </PageShell>
  );
}
