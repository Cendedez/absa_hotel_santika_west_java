"use client";

import { useRouter } from "next/navigation";

export default function LandingPage() {
  const router = useRouter();

  return (
    <main className="landing">
      <div className="card landing-card">
        <h1>Anotasi ABSA Hotel Santika</h1>
        <p className="subtitle">
          Validasi label Aspect-Based Sentiment Analysis oleh domain expert.
          Silakan pilih identitas Anda untuk memulai.
        </p>

        <div className="user-list">
          <button
            className="user-option"
            onClick={() => router.push("/researcher")}
          >
            <span>
              <span className="label">Researcher</span>
              <br />
              <span className="desc">Peneliti utama — bisa lihat progress semua user.</span>
            </span>
            <span className="arrow">→</span>
          </button>

          <button
            className="user-option"
            onClick={() => router.push("/expert1")}
          >
            <span>
              <span className="label">Hengky Kurniadi</span>
              <br />
              <span className="desc">Domain Expert 1</span>
            </span>
            <span className="arrow">→</span>
          </button>

          <button
            className="user-option"
            onClick={() => router.push("/expert2")}
          >
            <span>
              <span className="label">John Doe</span>
              <br />
              <span className="desc">Domain Expert 2</span>
            </span>
            <span className="arrow">→</span>
          </button>
        </div>

        <p className="muted" style={{ fontSize: "0.8rem", marginTop: 24 }}>
          Setiap user mengerjakan 50 review yang sama. Jawaban disimpan otomatis
          di browser (localStorage) dan dapat diekspor ke CSV.
        </p>
      </div>
    </main>
  );
}
