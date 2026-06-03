"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import reviewsData from "@/data/annotation_reviews.json";
import AspectForm from "@/components/AspectForm";
import ProgressPanel from "@/components/ProgressPanel";
import { ANNOTATORS } from "@/lib/constants";
import {
  emptyLabels,
  loadStore,
  saveStore,
  mergeStores,
} from "@/lib/storage";
import { pullStore, pushStore, type SyncState } from "@/lib/sync";
import {
  exportAnnotationsCsv,
  exportBackupJson,
  parseBackupJson,
} from "@/lib/exporters";
import type {
  AnnotationStore,
  AnnotatorId,
  AspectKey,
  ReviewItem,
  SentimentLabel,
} from "@/lib/types";

const REVIEWS = reviewsData as ReviewItem[];

interface Props {
  annotatorId: AnnotatorId;
  /** If true, show "Ganti user" button (only for researcher). */
  showSwitchUser?: boolean;
  onSwitchUser?: () => void;
}

export default function AnnotationPage({
  annotatorId,
  showSwitchUser = false,
  onSwitchUser,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const storeRef = useRef<AnnotationStore | null>(null);
  const pushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [store, setStore] = useState<AnnotationStore | null>(null);
  const [index, setIndex] = useState(0);
  const [labels, setLabels] = useState<Record<AspectKey, SentimentLabel>>(
    emptyLabels()
  );
  const [toast, setToast] = useState<string | null>(null);
  const [autosaved, setAutosaved] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>("idle");

  // keep a ref of the latest store for debounced push
  useEffect(() => {
    storeRef.current = store;
  }, [store]);

  // --- init: load local, then pull+merge from server ---
  useEffect(() => {
    let cancelled = false;
    const local = loadStore(annotatorId);
    setStore(local);

    (async () => {
      setSyncState("syncing");
      const result = await pullStore(annotatorId);
      if (cancelled) return;
      if (result.status === "disabled") {
        // sync disabled or unreachable -> work offline with local only
        setSyncState("disabled");
        return;
      }
      // sync works; server store may be null when nothing saved yet
      const merged = result.store ? mergeStores(local, result.store) : local;
      setStore(merged);
      saveStore(merged);
      // push merged back so server has the union too
      const confirmed = await pushStore(annotatorId, merged);
      if (cancelled) return;
      if (confirmed) {
        setStore(confirmed);
        saveStore(confirmed);
      }
      setSyncState("synced");
    })();

    return () => {
      cancelled = true;
    };
  }, [annotatorId]);

  // --- load labels when review changes ---
  useEffect(() => {
    if (!store) return;
    const review = REVIEWS[index];
    if (!review) return;
    const rec = store.records[review.ID_Review];
    setLabels(rec ? { ...rec.labels } : emptyLabels());
  }, [index, store]);

  const completedSet = useMemo(() => {
    const set = new Set<string>();
    if (store) {
      for (const [id, rec] of Object.entries(store.records)) {
        if (rec.saved) set.add(id);
      }
    }
    return set;
  }, [store]);

  // Debounced push to server.
  const schedulePush = useCallback(
    (s: AnnotationStore) => {
      if (syncState === "disabled") return;
      if (pushTimer.current) clearTimeout(pushTimer.current);
      pushTimer.current = setTimeout(async () => {
        setSyncState("syncing");
        const confirmed = await pushStore(annotatorId, s);
        if (confirmed) {
          // merge server's view back (in case another device added records)
          const merged = mergeStores(storeRef.current ?? s, confirmed);
          setStore(merged);
          saveStore(merged);
          setSyncState("synced");
        } else {
          setSyncState("offline");
        }
      }, 800);
    },
    [annotatorId, syncState]
  );

  if (!store) {
    return (
      <main className="container">
        <p className="muted">Memuat…</p>
      </main>
    );
  }

  const review = REVIEWS[index];
  const annotatorLabel =
    ANNOTATORS.find((a) => a.id === annotatorId)?.label ?? annotatorId;

  function showToast(msg: string) {
    setToast(msg);
    window.setTimeout(() => setToast(null), 1800);
  }

  function persist(
    nextLabels: Record<AspectKey, SentimentLabel>,
    markSaved: boolean
  ) {
    if (!store) return;
    const rev = REVIEWS[index];
    const prev = store.records[rev.ID_Review];
    const nextStore: AnnotationStore = {
      ...store,
      records: {
        ...store.records,
        [rev.ID_Review]: {
          labels: nextLabels,
          saved: markSaved || prev?.saved || false,
          annotated_at: new Date().toISOString(),
        },
      },
    };
    setStore(nextStore);
    saveStore(nextStore);
    setAutosaved(true);
    window.setTimeout(() => setAutosaved(false), 1200);
    schedulePush(nextStore);
  }

  function handleChange(aspect: AspectKey, value: SentimentLabel) {
    const next = { ...labels, [aspect]: value };
    setLabels(next);
    persist(next, false);
  }

  function handleSave() {
    persist(labels, true);
    showToast("Tersimpan ✓");
  }

  function handleResetCurrent() {
    const cleared = emptyLabels();
    setLabels(cleared);
    if (!store) return;
    const rev = REVIEWS[index];
    const nextRecords = { ...store.records };
    delete nextRecords[rev.ID_Review];
    const nextStore: AnnotationStore = {
      ...store,
      records: nextRecords,
      updated_at: new Date().toISOString(),
    };
    setStore(nextStore);
    saveStore(nextStore);
    schedulePush(nextStore);
    showToast("Review ini direset");
  }

  function go(delta: number) {
    setIndex((i) => Math.min(REVIEWS.length - 1, Math.max(0, i + delta)));
  }

  function handleExportCsv() {
    exportAnnotationsCsv(store!, REVIEWS);
    showToast("CSV diunduh");
    setMenuOpen(false);
  }

  function handleBackup() {
    exportBackupJson(store!);
    showToast("Backup JSON diunduh");
    setMenuOpen(false);
  }

  function handleImportClick() {
    fileInputRef.current?.click();
    setMenuOpen(false);
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const imported = parseBackupJson(text, annotatorId);
      const base = storeRef.current ?? imported;
      const merged = mergeStores(base, imported);
      setStore(merged);
      saveStore(merged);
      schedulePush(merged);
      const rev = REVIEWS[index];
      const rec = merged.records[rev.ID_Review];
      setLabels(rec ? { ...rec.labels } : emptyLabels());
      showToast("Backup berhasil diimport");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Gagal import backup.");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const isFirst = index === 0;
  const isLast = index === REVIEWS.length - 1;

  // Sync status label
  const syncLabel: Record<SyncState, { text: string; color: string }> = {
    idle: { text: "", color: "var(--text-muted)" },
    syncing: { text: "Menyinkronkan…", color: "var(--warning)" },
    synced: { text: "Tersinkron ke server ✓", color: "var(--success)" },
    offline: { text: "Offline — tersimpan lokal", color: "var(--danger)" },
    disabled: { text: "Mode lokal (tanpa server)", color: "var(--text-muted)" },
  };

  return (
    <>
      {/* Mobile menu overlay */}
      {menuOpen && (
        <div
          className="header-menu-overlay"
          onClick={() => setMenuOpen(false)}
        />
      )}

      {/* Mobile dropdown menu */}
      {menuOpen && (
        <div className="header-menu-dropdown">
          <div className="menu-header">
            <span className="menu-title">{annotatorLabel}</span>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setMenuOpen(false)}
            >
              ✕
            </button>
          </div>
          <hr className="divider" style={{ margin: "4px 0 8px" }} />
          <button className="btn btn-block" onClick={handleExportCsv}>
            📥 Export CSV
          </button>
          <button className="btn btn-block" onClick={handleBackup}>
            💾 Backup JSON
          </button>
          <button className="btn btn-block" onClick={handleImportClick}>
            📂 Import JSON
          </button>
          <button className="btn btn-block btn-ghost" onClick={handleResetCurrent}>
            🔄 Reset review ini
          </button>
          {showSwitchUser && onSwitchUser && (
            <>
              <hr className="divider" style={{ margin: "4px 0" }} />
              <button className="btn btn-block btn-ghost" onClick={onSwitchUser}>
                👤 Ganti user
              </button>
            </>
          )}
        </div>
      )}

      <main className="container" style={{ position: "relative" }}>
        {/* Header */}
        <header className="app-header">
          <div className="who">
            <span className="role">{annotatorLabel}</span>
            <span
              className="hint"
              style={{ color: syncLabel[syncState].color }}
            >
              {syncLabel[syncState].text || "Jawaban tersimpan otomatis"}
            </span>
          </div>

          {/* Desktop actions */}
          <div className="header-actions">
            <button className="btn btn-sm" onClick={handleExportCsv}>
              Export CSV
            </button>
            <button className="btn btn-sm" onClick={handleBackup}>
              Backup JSON
            </button>
            <button className="btn btn-sm" onClick={handleImportClick}>
              Import JSON
            </button>
            <button className="btn btn-sm btn-ghost" onClick={handleResetCurrent}>
              Reset
            </button>
            {showSwitchUser && onSwitchUser && (
              <button className="btn btn-sm btn-ghost" onClick={onSwitchUser}>
                Ganti user
              </button>
            )}
          </div>

          {/* Mobile hamburger */}
          <button
            className="header-menu-btn"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Menu"
          >
            ☰
          </button>
        </header>

        <input
          ref={fileInputRef}
          type="file"
          accept="application/json"
          style={{ display: "none" }}
          onChange={handleImportFile}
        />

        {/* Progress */}
        <ProgressPanel
          reviews={REVIEWS}
          completed={completedSet}
          currentIndex={index}
          onJump={(i) => setIndex(i)}
        />

        {/* Review card */}
        <div className="card" style={{ marginTop: 16 }}>
          <div className="review-header-row">
            <h2>
              Review {index + 1}{" "}
              <span className="muted" style={{ fontWeight: 400 }}>
                dari {REVIEWS.length}
              </span>
            </h2>
            {autosaved && (
              <span className="autosave">
                <span className="dot" /> Autosaved
              </span>
            )}
          </div>

          <div className="review-meta">
            <span><b>ID:</b> {review.ID_Review}</span>
            <span><b>Platform:</b> {review.Platform}</span>
            <span><b>Hotel:</b> {review.Nama_Hotel}</span>
            <span><b>Tanggal:</b> {review.Review_Date}</span>
          </div>

          <div className="review-text">{review.Text_Review}</div>

          <div className="instruction">
            Silakan beri label sentimen untuk setiap aspek berdasarkan isi
            review. Pilih <b>None</b> apabila aspek tidak dibahas.
          </div>

          <AspectForm labels={labels} onChange={handleChange} />

          {/* Desktop nav */}
          <div className="nav-bar">
            <div className="nav-left">
              <button className="btn" onClick={() => go(-1)} disabled={isFirst}>
                ← Previous
              </button>
              <button className="btn" onClick={() => go(1)} disabled={isLast}>
                Next →
              </button>
            </div>
            <div className="nav-right">
              <button className="btn btn-primary" onClick={handleSave}>
                Simpan ✓
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Mobile sticky bottom nav */}
      <nav className="bottom-nav">
        <button className="btn nav-prev" onClick={() => go(-1)} disabled={isFirst}>
          ← Prev
        </button>
        <button className="btn btn-primary nav-save" onClick={handleSave}>
          Simpan ✓
        </button>
        <button className="btn nav-next" onClick={() => go(1)} disabled={isLast}>
          Next →
        </button>
      </nav>

      {toast && <div className="toast">{toast}</div>}
    </>
  );
}
