// Shared types for the annotation app.

export type AspectKey =
  | "Lokasi"
  | "Kenyamanan"
  | "Pelayanan"
  | "Kebersihan"
  | "Harga"
  | "Makanan"
  | "Fasilitas";

export type SentimentLabel = "None" | "positif" | "negatif" | "netral";

export type AnnotatorId = "researcher" | "expert_1" | "expert_2";

// A single review shown to the annotator (NO labels included).
export interface ReviewItem {
  ID_Review: string;
  Platform: string;
  Nama_Hotel: string;
  Review_Date: string;
  Text_Review: string;
}

// Per-review annotation record stored in localStorage.
export interface AnnotationRecord {
  labels: Record<AspectKey, SentimentLabel>;
  saved: boolean; // marked done when user saves
  annotated_at: string | null; // ISO timestamp of last save
}

// The whole localStorage payload for one annotator.
export interface AnnotationStore {
  annotator_id: AnnotatorId;
  version: number;
  // keyed by ID_Review
  records: Record<string, AnnotationRecord>;
  updated_at: string;
}
