import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anotasi ABSA Hotel Santika",
  description:
    "Website anotasi domain expert untuk validasi label ABSA review Hotel Santika.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
