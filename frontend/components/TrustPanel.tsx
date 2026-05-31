export function TrustPanel() {
  return (
    <section className="trust-panel">
      <div>
        <p className="status-label">Trust check</p>
        <h2>Target-aware sentiment, not generic positivity.</h2>
      </div>
      <ul>
        <li>Meroq now asks whether a headline is positive or cautionary for the selected company.</li>
        <li>Low-relevance or uncertain headlines are down-weighted instead of forcing a direction.</li>
        <li>Reason tags explain why a headline was scored, but source articles remain the final evidence.</li>
      </ul>
    </section>
  );
}
