"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Demo = {
  id: string;
  prospect_name: string;
  company_url: string;
  logo_url?: string | null;
  public_slug: string;
  chat_url: string;
  status: string;
  expires_at: string;
  created_at: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000";

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function displayDomain(url: string) {
  try {
    return new URL(url).host;
  } catch {
    return url.replace(/^https?:\/\//, "");
  }
}

export default function Home() {
  const [demos, setDemos] = useState<Demo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const demosEndpoint = useMemo(() => `${API_BASE_URL}/api/v1/demos`, []);

  const loadDemos = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(demosEndpoint, { method: "GET" });
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(data.detail || `Failed to load demos (${response.status})`);
      }
      const data = (await response.json()) as Demo[];
      setDemos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demos");
    } finally {
      setLoading(false);
    }
  }, [demosEndpoint]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadDemos();
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadDemos]);

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
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => void loadDemos()}
              className="inline-flex h-11 items-center justify-center rounded-xl border bg-white px-5 text-sm font-semibold text-[var(--primary)] transition hover:bg-[var(--surface-soft)]"
            >
              Refresh
            </button>
            <button
              type="button"
              className="inline-flex h-11 items-center justify-center rounded-xl bg-[var(--accent)] px-5 text-sm font-semibold text-white transition hover:brightness-95"
            >
              Create Demo
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border bg-[var(--surface)] p-6 shadow-sm">
        {loading && (
          <div className="rounded-xl border border-dashed p-10 text-center text-sm text-[var(--muted)]">
            Loading active demos from backend...
          </div>
        )}

        {!loading && error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-[var(--error)]">
            <p className="font-semibold">Could not load active demos.</p>
            <p className="mt-1">{error}</p>
            <p className="mt-2 text-xs text-red-700">Endpoint: {demosEndpoint}</p>
          </div>
        )}

        {!loading && !error && demos.length === 0 && (
          <div className="rounded-xl border border-dashed p-10 text-center">
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
              Empty State
            </p>
            <h2 className="mt-3 text-xl font-semibold text-[var(--primary)]">
              No active demos yet
            </h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-[var(--muted)]">
              The backend returned zero active, unexpired demos from <span className="font-semibold">/api/v1/demos</span>.
            </p>
          </div>
        )}

        {!loading && !error && demos.length > 0 && (
          <div className="grid gap-4">
            {demos.map((demo) => {
              const chatHref = demo.chat_url.startsWith("http") ? demo.chat_url : demo.chat_url;
              return (
                <article
                  key={demo.id}
                  className="rounded-2xl border bg-white/70 p-4 shadow-sm transition hover:border-[var(--accent)] hover:bg-white"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex min-w-0 items-center gap-3">
                      {demo.logo_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={demo.logo_url}
                          alt={`${demo.prospect_name} logo`}
                          className="h-12 w-12 shrink-0 rounded-xl border bg-white object-contain p-2"
                        />
                      ) : (
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-sm font-bold uppercase text-white">
                          {demo.prospect_name.slice(0, 2)}
                        </div>
                      )}
                      <div className="min-w-0">
                        <h2 className="truncate text-lg font-semibold text-[var(--primary)]">
                          {demo.prospect_name}
                        </h2>
                        <a
                          href={demo.company_url}
                          target="_blank"
                          rel="noreferrer"
                          className="block truncate text-sm text-[var(--muted)] hover:text-[var(--accent)]"
                        >
                          {displayDomain(demo.company_url)}
                        </a>
                        <p className="mt-1 text-xs text-[var(--muted)]">
                          Expires: {formatDate(demo.expires_at)}
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-2 sm:shrink-0">
                      <a
                        href={chatHref}
                        className="inline-flex h-10 items-center justify-center rounded-xl bg-[var(--primary)] px-4 text-sm font-semibold text-white transition hover:brightness-110"
                      >
                        Open Chat
                      </a>
                      <button
                        type="button"
                        onClick={() => void navigator.clipboard.writeText(`${window.location.origin}${demo.chat_url}`)}
                        className="inline-flex h-10 items-center justify-center rounded-xl border bg-white px-4 text-sm font-semibold text-[var(--primary)] transition hover:bg-[var(--surface-soft)]"
                      >
                        Copy Link
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
