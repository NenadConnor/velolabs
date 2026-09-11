import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "velolabs.io — Design workspace",
  description: "Describe, generate and inspect editable CAD assemblies with Ollama and text-to-cad.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
