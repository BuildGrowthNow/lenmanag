import { Badge } from "@/components/ui/badge";
import type { RefinementPromptRecord } from "@/lib/types";

export function PromptHistory({
  prompts,
  currentPromptId
}: {
  prompts: RefinementPromptRecord[];
  currentPromptId?: string | null;
}) {
  if (!prompts.length) return null;

  return (
    <div className="rounded-2xl border border-line bg-panel-2 p-6">
      <h3 className="mb-4 text-sm font-semibold text-text">Refinement History</h3>
      <div className="space-y-3">
        {prompts.map((prompt) => {
          const submittedAt = prompt.submittedAt ? new Date(prompt.submittedAt) : null;
          const isCurrent = currentPromptId && prompt.id === currentPromptId;

          return (
            <div
              key={prompt.id}
              className={`rounded-lg border p-3 ${
                isCurrent ? "border-accent bg-accent/10" : "border-line bg-panel"
              }`}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-medium text-text">
                  {submittedAt ? submittedAt.toLocaleString() : ""}
                </span>
                <Badge
                  className={
                    prompt.status === "success"
                      ? "border-green-500/40 bg-green-500/10 text-green-100"
                      : prompt.status === "failed"
                        ? "border-rose-500/40 bg-rose-500/10 text-rose-100"
                        : "border-blue-500/40 bg-blue-500/10 text-blue-100"
                  }
                >
                  {prompt.status}
                </Badge>
              </div>
              <p className="text-sm italic text-muted">"{prompt.promptText}"</p>
              {prompt.qualityScore !== null && prompt.qualityScore !== undefined ? (
                <div className="mt-2 text-xs text-text">
                  Quality Score: {prompt.qualityScore}/100
                </div>
              ) : null}
              {prompt.failureReason ? (
                <div className="mt-2 text-xs text-rose-400">{prompt.failureReason}</div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
