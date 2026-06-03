import { createClient, SupabaseClient } from "@supabase/supabase-js";

// Server-side Supabase client.
// Uses the SERVICE ROLE key which must NEVER be exposed to the browser.
// These env vars are read only inside API routes (server runtime).

let cached: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    // Not configured — caller should handle gracefully.
    return null;
  }
  if (cached) return cached;
  cached = createClient(url, key, {
    auth: { persistSession: false },
  });
  return cached;
}

export const ANNOTATIONS_TABLE = "annotations";
