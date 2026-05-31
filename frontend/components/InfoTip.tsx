type InfoTipProps = {
  label: string;
  children: string;
};

export function InfoTip({ label, children }: InfoTipProps) {
  return (
    <span className="info-tip" tabIndex={0} aria-label={`${label}: ${children}`}>
      <span aria-hidden="true">i</span>
      <span className="info-tip-panel" role="tooltip">
        {children}
      </span>
    </span>
  );
}
