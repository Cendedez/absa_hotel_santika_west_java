"use client";

import type { ReviewItem } from "@/lib/types";

interface Props {
  reviews: ReviewItem[];
  completed: Set<string>;
  currentIndex: number;
  onJump: (index: number) => void;
}

export default function ProgressPanel({
  reviews,
  completed,
  currentIndex,
  onJump,
}: Props) {
  const total = reviews.length;
  const done = completed.size;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <div className="progress-wrap card">
      <div className="progress-meta">
        <span>
          Selesai: <b>{done}</b> dari {total}
        </span>
        <span>{pct}%</span>
      </div>
      <div className="progress-bar">
        <span style={{ width: `${pct}%` }} />
      </div>

      <p className="section-title" style={{ marginTop: 18 }}>
        Lompat ke review
      </p>
      <div className="jump-grid">
        {reviews.map((r, i) => {
          const isDone = completed.has(r.ID_Review);
          const isCurrent = i === currentIndex;
          const cls = [
            "jump-cell",
            isDone ? "done" : "",
            isCurrent ? "current" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              key={r.ID_Review}
              className={cls}
              onClick={() => onJump(i)}
              title={`Review ${i + 1} (ID ${r.ID_Review})${
                isDone ? " - selesai" : ""
              }`}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
    </div>
  );
}
