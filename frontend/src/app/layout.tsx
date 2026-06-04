import type { Metadata } from "next";

// @ts-ignore - Suppress TS2882: Ingest global styles via side-effect import without type declarations
import "./globals.css"; // Ingest global styles at the absolute top-level layout

/**
 * Application Metadata configuration object.
 * Next.js automatically parses this exported metadata config to inject matching
 * HTML <title> and <meta> elements into the generated page document head.
 */
export const metadata: Metadata = {
  title: "InsightX Platform",
  description: "Agentic Enterprise Banking Reporting Engine",
};

/**
 * Root Layout Component.
 * Acts as the foundational structural HTML wrapper for the entire web client.
 * All pages and nested layout templates route within this component layout wrapper.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {/* Render nested feature routing pages (e.g., /datasources/add) here */}
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  );
}
