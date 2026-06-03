"use client";

import { ASPECTS, SENTIMENT_OPTIONS } from "@/lib/constants";
import type { AspectKey, SentimentLabel } from "@/lib/types";

interface Props {
  labels: Record<AspectKey, SentimentLabel>;
  onChange: (aspect: AspectKey, value: SentimentLabel) => void;
}

export default function AspectForm({ labels, onChange }: Props) {
  return (
    <div className="aspect-grid">
      {ASPECTS.map((aspect) => (
        <fieldset className="aspect-row" key={aspect}>
          <div className="aspect-name">{aspect}</div>
          <div className="option-list">
            {SENTIMENT_OPTIONS.map((opt) => {
              const checked = labels[aspect] === opt.value;
              return (
                <label
                  key={opt.value}
                  className={checked ? "checked" : ""}
                >
                  <input
                    type="radio"
                    name={`aspect-${aspect}`}
                    value={opt.value}
                    checked={checked}
                    onChange={() => onChange(aspect, opt.value)}
                  />
                  {opt.label}
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
