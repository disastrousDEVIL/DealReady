export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8">
      <section className="rounded-2xl border bg-[var(--surface)] p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Internal Sales Console
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--primary)]">
              Active Demo Links
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Create and share prospect-specific chatbot demos from one place.
            </p>
          </div>
          <button
            type="button"
            className="inline-flex h-11 items-center justify-center rounded-xl bg-[var(--accent)] px-5 text-sm font-semibold text-white transition hover:brightness-95"
          >
            Create Demo
          </button>
        </div>
      </section>

      <section className="rounded-2xl border bg-[var(--surface)] p-6 shadow-sm">
        <div className="rounded-xl border border-dashed p-10 text-center">
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
            Empty State
          </p>
          <h2 className="mt-3 text-xl font-semibold text-[var(--primary)]">
            No active demos yet
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-sm text-[var(--muted)]">
            Click <span className="font-semibold">Create Demo</span> to crawl a company URL,
            upload optional PDFs, and generate a shareable chatbot link.
          </p>
        </div>
      </section>
    </main>
  );
}
