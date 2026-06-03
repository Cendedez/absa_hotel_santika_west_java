import type { AnnotationStore, AnnotatorId, ReviewItem } from "./types";
import { getRecord } from "./storage";

// Safe CSV field escaping (handles commas, quotes, newlines).
function csvField(value: string): string {
  const v = value ?? "";
  if (/[",\n\r]/.test(v)) {
    return '"' + v.replace(/"/g, '""') + '"';
  }
  return v;
}

function triggerDownload(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Export annotations to CSV (only the columns requested in the spec).
export function exportAnnotationsCsv(
  store: AnnotationStore,
  reviews: ReviewItem[]
): void {
  const header = [
    "annotator_id",
    "ID_Review",
    "Platform",
    "Nama_Hotel",
    "Review_Date",
    "Text_Review",
    "Lokasi",
    "Kenyamanan",
    "Pelayanan",
    "Kebersihan",
    "Harga",
    "Makanan",
    "Fasilitas",
    "annotated_at",
  ];

  const lines: string[] = [header.join(",")];

  for (const review of reviews) {
    const rec = getRecord(store, review.ID_Review);
    const row = [
      store.annotator_id,
      review.ID_Review,
      review.Platform,
      review.Nama_Hotel,
      review.Review_Date,
      review.Text_Review,
      rec.labels.Lokasi,
      rec.labels.Kenyamanan,
      rec.labels.Pelayanan,
      rec.labels.Kebersihan,
      rec.labels.Harga,
      rec.labels.Makanan,
      rec.labels.Fasilitas,
      rec.annotated_at ?? "",
    ].map((x) => csvField(String(x)));
    lines.push(row.join(","));
  }

  // Add BOM so Excel reads UTF-8 correctly.
  const content = "\ufeff" + lines.join("\r\n");
  triggerDownload(`annotations_${store.annotator_id}.csv`, content, "text/csv;charset=utf-8;");
}

// Export full localStorage payload as a JSON backup.
export function exportBackupJson(store: AnnotationStore): void {
  const content = JSON.stringify(store, null, 2);
  triggerDownload(
    `backup_${store.annotator_id}_${new Date().toISOString().slice(0, 10)}.json`,
    content,
    "application/json"
  );
}

// Validate and import a JSON backup. Returns the store if valid, else throws.
export function parseBackupJson(text: string, expected: AnnotatorId): AnnotationStore {
  const parsed = JSON.parse(text) as AnnotationStore;
  if (!parsed || typeof parsed !== "object" || !parsed.records) {
    throw new Error("Format backup tidak valid.");
  }
  if (parsed.annotator_id !== expected) {
    throw new Error(
      `Backup ini milik "${parsed.annotator_id}", bukan "${expected}". ` +
        "Silakan masuk sebagai user yang sesuai sebelum import."
    );
  }
  return parsed;
}
