"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

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

type CreatedDemo = Demo & {
  generated_password: string;
  vector_store_id: string;
  pages_crawled: number;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000";
const MAX_PDFS = 5;
const MAX_PDF_BYTES = 25 * 1024 * 1024;

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

function absoluteChatUrl(chatUrl: string) {
  if (chatUrl.startsWith("http")) return chatUrl;
  return `${window.location.origin}${chatUrl}`;
}

export default function Home() {
  const [demos, setDemos] = useState<Demo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createdDemo, setCreatedDemo] = useState<CreatedDemo | null>(null);
  const [prospectName, setProspectName] = useState("");
  const [companyUrl, setCompanyUrl] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [files, setFiles] = useState<File[]>([]);

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

  function resetCreateForm() {
    setProspectName("");
    setCompanyUrl("");
    setLogoUrl("");
    setFiles([]);
    setCreateError("");
    setCreatedDemo(null);
  }

  function onFileChange(nextFiles: FileList | null) {
    const selected = Array.from(nextFiles || []);
    if (selected.length > MAX_PDFS) {
      setCreateError(`Maximum ${MAX_PDFS} PDFs are allowed.`);
      setFiles([]);
      return;
    }
    const invalid = selected.find(
      (file) => file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf"),
    );
    if (invalid) {
      setCreateError("Only PDF files are allowed.");
      setFiles([]);
      return;
    }
    const oversized = selected.find((file) => file.size > MAX_PDF_BYTES);
    if (oversized) {
      setCreateError("Each PDF must be 25 MB or less.");
      setFiles([]);
      return;
    }
    setCreateError("");
    setFiles(selected);
  }

  async function createDemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (creating) return;

    setCreateError("");
    setCreatedDemo(null);

    if (!prospectName.trim() || !companyUrl.trim()) {
      setCreateError("Prospect name and company URL are required.");
      return;
    }

    const formData = new FormData();
    formData.append("prospect_name", prospectName.trim());
    formData.append("company_url", companyUrl.trim());
    if (logoUrl.trim()) formData.append("logo_url", logoUrl.trim());
    files.forEach((file) => formData.append("files", file));

    setCreating(true);
    try {
      const response = await fetch(demosEndpoint, {
        method: "POST",
        body: formData,
      });
      const data = (await response.json().catch(() => ({}))) as CreatedDemo | { detail?: string };
      if (!response.ok) {
        throw new Error((data as { detail?: string }).detail || `Create demo failed (${response.status})`);
      }
      setCreatedDemo(data as CreatedDemo);
      await loadDemos();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Create demo failed");
    } finally {
      setCreating(false);
    }
  }

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
              onClick={() => {
                resetCreateForm();
                setModalOpen(true);
              }}
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
                        onClick={() => void navigator.clipboard.writeText(absoluteChatUrl(demo.chat_url))}
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

      {modalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 px-4 backdrop-blur-sm">
          <div className="max-h-[90dvh] w-full max-w-2xl overflow-y-auto rounded-2xl border bg-[var(--surface)] p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  New Prospect Demo
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-[var(--primary)]">
                  Create Demo
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-full border bg-white px-3 py-1 text-sm font-semibold text-[var(--primary)]"
              >
                Close
              </button>
            </div>

            {createdDemo ? (
              <div className="mt-6 rounded-xl border bg-white p-5">
                <p className="text-sm font-semibold text-[var(--success)]">Demo created successfully.</p>
                <div className="mt-4 space-y-3 text-sm">
                  <div>
                    <p className="font-semibold text-[var(--primary)]">Chat URL</p>
                    <a
                      href={createdDemo.chat_url}
                      className="break-all text-[var(--accent)] underline underline-offset-4"
                    >
                      {absoluteChatUrl(createdDemo.chat_url)}
                    </a>
                  </div>
                  <div>
                    <p className="font-semibold text-[var(--primary)]">Generated Password</p>
                    <p className="font-mono text-lg">{createdDemo.generated_password}</p>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => void navigator.clipboard.writeText(absoluteChatUrl(createdDemo.chat_url))}
                      className="rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white"
                    >
                      Copy Link
                    </button>
                    <button
                      type="button"
                      onClick={() => void navigator.clipboard.writeText(createdDemo.generated_password)}
                      className="rounded-xl border bg-white px-4 py-2 text-sm font-semibold text-[var(--primary)]"
                    >
                      Copy Password
                    </button>
                    <button
                      type="button"
                      onClick={resetCreateForm}
                      className="rounded-xl border bg-white px-4 py-2 text-sm font-semibold text-[var(--primary)]"
                    >
                      Create Another
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <form className="mt-6 space-y-4" onSubmit={createDemo}>
                <label className="block text-sm font-semibold text-[var(--primary)]">
                  Prospect name
                  <input
                    value={prospectName}
                    onChange={(event) => setProspectName(event.target.value)}
                    className="mt-2 h-11 w-full rounded-xl border bg-white px-3 text-sm font-normal outline-none focus:ring-2 focus:ring-[var(--accent)]"
                    placeholder="Capital Numbers"
                    required
                  />
                </label>

                <label className="block text-sm font-semibold text-[var(--primary)]">
                  Company URL
                  <input
                    value={companyUrl}
                    onChange={(event) => setCompanyUrl(event.target.value)}
                    className="mt-2 h-11 w-full rounded-xl border bg-white px-3 text-sm font-normal outline-none focus:ring-2 focus:ring-[var(--accent)]"
                    placeholder="https://www.capitalnumbers.com/"
                    required
                  />
                </label>

                <label className="block text-sm font-semibold text-[var(--primary)]">
                  Logo URL
                  <input
                    value={logoUrl}
                    onChange={(event) => setLogoUrl(event.target.value)}
                    className="mt-2 h-11 w-full rounded-xl border bg-white px-3 text-sm font-normal outline-none focus:ring-2 focus:ring-[var(--accent)]"
                    placeholder="https://example.com/logo.svg"
                  />
                </label>

                <div>
                  <p className="text-sm font-semibold text-[var(--primary)]">PDFs optional</p>
                  <label className="mt-2 flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed bg-white px-5 py-6 text-center transition hover:border-[var(--accent)] hover:bg-[var(--surface-soft)]">
                    <input
                      type="file"
                      accept="application/pdf,.pdf"
                      multiple
                      onChange={(event) => onFileChange(event.target.files)}
                      className="sr-only"
                    />
                    <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--primary)] text-xl font-semibold text-white">
                      +
                    </span>
                    <span className="mt-3 text-sm font-semibold text-[var(--primary)]">
                      Attach PDF files
                    </span>
                    <span className="mt-1 text-xs text-[var(--muted)]">
                      Optional. Maximum 5 PDFs, 25 MB each.
                    </span>
                  </label>

                  {files.length > 0 ? (
                    <div className="mt-3 rounded-xl border bg-white p-3 text-xs text-[var(--muted)]">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <p className="font-semibold text-[var(--primary)]">
                          {files.length} PDF{files.length > 1 ? "s" : ""} selected
                        </p>
                        <button
                          type="button"
                          onClick={() => setFiles([])}
                          className="font-semibold text-[var(--accent)]"
                        >
                          Clear
                        </button>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {files.map((file) => (
                          <span
                            key={`${file.name}-${file.size}`}
                            className="max-w-full truncate rounded-full border bg-[var(--surface)] px-3 py-1"
                          >
                            {file.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="mt-2 text-xs text-[var(--muted)]">
                      No PDFs attached. The demo will still be created from the company URL.
                    </p>
                  )}
                </div>

                {createError && (
                  <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-[var(--error)]">
                    {createError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={creating}
                  className="h-12 w-full rounded-xl bg-[var(--accent)] px-5 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {creating ? "Creating demo..." : "Create Demo"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
