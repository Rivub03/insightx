/**
 * Root Route Page Component for InsightX Platform
 * Path: frontend/src/app/page.tsx
 * * Next.js App Router mandates that the 'page.tsx' file inside any routing folder
 * must expose a valid React element or component function via a DEFAULT export statement.
 */

import React from "react";

// Example placeholder for the actual connection module form component
// import DataSourceForm from "@/features/datasources/components/DataSourceForm";

export default function RootPage() {
  return (
    <main className="min-h-screen bg-slate-50 p-8 flex flex-col items-center justify-center">
      <div className="w-full max-w-4xl bg-white shadow-xl rounded-2xl p-8 border border-slate-200">
        <header className="mb-6 border-b border-slate-100 pb-4">
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            InsightX Platform Onboarding
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Module 1 — Relational OLAP Database Connector Registration &
            Configuration
          </p>
        </header>

        {/* Content Section: Render database connection modules here */}
        <section className="py-4">
          <p className="text-slate-700">
            Welcome to InsightX. Select your target engine (Oracle, PostgreSQL,
            or MS SQL Server) to configure safe data dictionary mappings.
          </p>

          {/* <DataSourceForm /> */}
        </section>
      </div>
    </main>
  );
}
