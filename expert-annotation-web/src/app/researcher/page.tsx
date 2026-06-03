"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import AnnotationPage from "@/components/AnnotationPage";
import ProgressDashboard from "@/components/ProgressDashboard";

export default function ResearcherPage() {
  const router = useRouter();
  const [view, setView] = useState<"annotate" | "dashboard">("annotate");

  if (view === "dashboard") {
    return (
      <main className="container">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Dashboard Progress</h2>
          <button className="btn btn-sm" onClick={() => setView("annotate")}>
            ← Kembali ke Anotasi
          </button>
        </div>
        <ProgressDashboard />
      </main>
    );
  }

  return (
    <>
      {/* Floating dashboard button for researcher */}
      <div style={{ position: "fixed", top: 12, right: 12, zIndex: 35 }}>
        <button
          className="btn btn-sm btn-primary"
          onClick={() => setView("dashboard")}
        >
          📊 Dashboard
        </button>
      </div>
      <AnnotationPage
        annotatorId="researcher"
        showSwitchUser={true}
        onSwitchUser={() => router.push("/")}
      />
    </>
  );
}
