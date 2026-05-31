export function TrustPanel() {
  return (
    <section className="trust-panel">
      <div>
        <p className="status-label">Trust check</p>
        <h2>Read the source before trusting the score.</h2>
      </div>
      <ul>
        <li>Sentiment is a summary of recent headlines, not proof of market direction.</li>
        <li>Open the original article when a headline materially changes the signal.</li>
        <li>Use risk and model confidence together; do not rely on sentiment alone.</li>
      </ul>
    </section>
  );
}
