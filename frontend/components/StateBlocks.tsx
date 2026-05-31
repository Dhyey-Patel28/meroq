export function LoadingState({ label = "Running analysis..." }: { label?: string }) {
  return (
    <section className="card subtle-card">
      <div className="loader-row">
        <span className="spinner" />
        <div>
          <h3>{label}</h3>
          <p className="muted">Local models and data providers may take a few seconds on the first run.</p>
        </div>
      </div>
    </section>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <section className="error">
      <strong>Something went wrong</strong>
      <p>{message}</p>
    </section>
  );
}
