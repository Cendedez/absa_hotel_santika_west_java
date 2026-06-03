import { NextResponse } from "next/server";
import { getSupabase, ANNOTATIONS_TABLE } from "@/lib/supabaseServer";
import { PROGRESS_RESET_AT, STORAGE_VERSION } from "@/lib/constants";
import type { AnnotationStore } from "@/lib/types";

export const dynamic = "force-dynamic";
const RESET_TIME = Date.parse(PROGRESS_RESET_AT);

// GET /api/progress -> live completed counts for all annotators from the server.
export async function GET() {
  const sb = getSupabase();
  if (!sb) {
    return NextResponse.json(
      { error: "sync_disabled", message: "Supabase belum dikonfigurasi." },
      { status: 503 }
    );
  }

  const { data, error } = await sb
    .from(ANNOTATIONS_TABLE)
    .select("annotator_id, store, updated_at");

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const progress: Record<
    string,
    { completed: number; updated_at: string | null }
  > = {};

  for (const row of data ?? []) {
    const store = row.store as AnnotationStore | null;
    let completed = 0;
    if (store && store.records && (store.version ?? 1) >= STORAGE_VERSION) {
      completed = Object.values(store.records).filter((r) => {
        if (!r.saved || !r.annotated_at) return false;
        const t = Date.parse(r.annotated_at);
        return Number.isFinite(t) && t >= RESET_TIME;
      }).length;
    }
    progress[row.annotator_id] = {
      completed,
      updated_at: row.updated_at ?? null,
    };
  }

  return NextResponse.json({ progress });
}
