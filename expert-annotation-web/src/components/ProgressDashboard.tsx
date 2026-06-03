"use client";

import { useCallback, useEffect, useState } from "react";
import reviewsData from "@/data/annotation_reviews.json";
import { ANNOTATORS } from "@/lib/constants";
import { loadStore, countCompleted } from "@/lib/storage";
import { fetchProgress } from "@/lib/sync";
import type { AnnotatorId } from "@/lib/types";

const TOTAL_REVIEWS = reviewsData.length;

interface UserProgress {
  id: AnnotatorId;
  label: string;
  completed: number;
  total: number;
  updatedAt: string | null;
}

export default function ProgressDashboard() {
  const [progress, setProgress] = useState<UserProgress[]>([]);
  const [source, setSource] = useState<"server" | "local">("local");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const server = await fetchProgress();

    if (server) {
      const results: UserProgress[] = ANNOTATORS.map((a) => ({
        id: a.id,
        label: a.label,
        completed: server[a.id]?.completed ?? 0,
        total: TOTAL_REVIEWS,
        updatedAt: server[a.id]?.updated_at ?? null,
      }));
      setProgress(results);
      setSource("server");
    } else {
      // fallback to local-only counts
      const results: UserProgress[] = ANNOTATORS.map((a) => {
        const store = loadStore(a.id);
        return {
          id: a.id,
          label: a.label,
          completed: countCompleted(store),
          total: TOTAL_REVIEWS,
          updatedAt: null,
        };
      });
      setProgress(results);
      setSource("local");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    // auto-refresh every 15s when viewing server data
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  function fmtTime(iso: string | null): string {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("id-ID", {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span className="muted" style={{ fontSize: "0.82rem" }}>
          {source === "server"
            ? "Sumber: server (real-time)"
            : "Sumber: lokal (server tidak aktif)"}
          {loading ? " · memuat…" : ""}
        </span>
        <button className="btn btn-sm" onClick={load} disabled={loading}>
          ⟳ Refresh
        </button>
      </div>

      {progress.map((p) => {
        const pct = Math.round((p.completed / p.total) * 100);
        return (
          <div key={p.id} className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <div>
                <strong>{p.label}</strong>
                <span
                  className="muted"
                  style={{ marginLeft: 8, fontSize: "0.85rem" }}
                >
                  ({p.id})
                </span>
              </div>
              <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>
                {p.completed}/{p.total}
              </span>
            </div>
            <div className="progress-bar">
              <span style={{ width: `${pct}%` }} />
            </div>
            <div
              className="muted"
              style={{
                fontSize: "0.8rem",
                marginTop: 6,
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span>{pct}% selesai</span>
              {source === "server" && (
                <span>Update: {fmtTime(p.updatedAt)}</span>
              )}
            </div>
          </div>
        );
      })}

      {source === "local" && (
        <div className="card" style={{ background: "var(--primary-soft)" }}>
          <p style={{ margin: 0, fontSize: "0.88rem", color: "#2a4a6b" }}>
            <strong>Catatan:</strong> Server sinkronisasi belum aktif, jadi
            dashboard hanya menampilkan progress dari browser ini. Setelah
            Supabase dikonfigurasi (lihat README), progress semua expert akan
            tampil otomatis & real-time.
          </p>
        </div>
      )}
    </div>
  );
}
