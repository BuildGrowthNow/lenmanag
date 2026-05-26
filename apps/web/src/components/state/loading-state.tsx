export function LoadingState({ label = "Loading shell..." }: { label?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel px-4 py-5 text-sm text-muted">
      <div className="animate-pulse">{label}</div>
    </div>
  );
}

