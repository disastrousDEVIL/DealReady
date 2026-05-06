"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Citation = {
  type?: string;
  filename?: string;
  title?: string;
  url?: string;
  number?: number;
};

type QueryResponse = {
  answer: string;
  response_id: string;
  previous_response_id?: string | null;
  citations?: Citation[];
};

type AuthResponse = {
  authenticated: boolean;
  requires_password: boolean;
};

type DemoMetaResponse = {
  prospect_name: string;
  logo_url?: string | null;
};

type Message = {
  role: "user" | "assistant" | "error";
  text: string;
  citations?: Citation[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000";

function citationLabel(citation: Citation): string {
  return citation.filename || citation.title || citation.url || "Source";
}

export default function DemoChatPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [password, setPassword] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [demoName, setDemoName] = useState("Demo Chat");
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [previousResponseId, setPreviousResponseId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Ask any question about this demo. I will answer from the indexed website and uploaded PDFs.",
    },
  ]);

  const endpoint = useMemo(() => `${API_BASE_URL}/api/v1/demos/${slug}/query`, [slug]);
  const authEndpoint = useMemo(() => `${API_BASE_URL}/api/v1/demos/${slug}/auth`, [slug]);
  const demoMetaEndpoint = useMemo(() => `${API_BASE_URL}/api/v1/demos/${slug}`, [slug]);

  useEffect(() => {
    let active = true;
    async function loadDemoMeta() {
      try {
        const response = await fetch(demoMetaEndpoint, {
          method: "GET",
        });
        if (!response.ok) return;
        const data = (await response.json()) as DemoMetaResponse;
        if (!active) return;
        setDemoName(data.prospect_name || "Demo Chat");
        setLogoUrl(data.logo_url || null);
      } catch {
        // Non-blocking: keep fallback title if metadata load fails.
      }
    }

    async function bootstrapAuth() {
      try {
        const response = await fetch(authEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ access_password: null }),
        });
        if (response.ok) {
          const data = (await response.json()) as AuthResponse;
          if (!active) return;
          if (!data.requires_password && data.authenticated) {
            setIsUnlocked(true);
          }
          return;
        }
        if (response.status === 401) {
          return;
        }
        const data = (await response.json()) as { detail?: string };
        if (!active) return;
        setAuthError(data.detail || "Failed to initialize chat access.");
      } catch {
        if (!active) return;
        setAuthError("Unable to reach backend for authentication.");
      }
    }
    loadDemoMeta();
    bootstrapAuth();
    return () => {
      active = false;
    };
  }, [authEndpoint, demoMetaEndpoint]);

  async function onUnlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authLoading) return;

    setAuthError("");
    setAuthLoading(true);
    try {
      const response = await fetch(authEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_password: password || null }),
      });
      const data = (await response.json()) as AuthResponse | { detail?: string };
      if (!response.ok) {
        throw new Error((data as { detail?: string }).detail || "Authentication failed");
      }

      const typed = data as AuthResponse;
      setIsUnlocked(typed.authenticated);
      if (typed.authenticated) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: typed.requires_password
              ? "Password verified. You can now ask questions."
              : "No password required. You can now ask questions.",
          },
        ]);
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setAuthLoading(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isUnlocked) return;
    const prompt = question.trim();
    if (!prompt || loading) return;

    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", text: prompt }]);
    setLoading(true);

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: prompt,
          previous_response_id: previousResponseId,
          access_password: password || null,
        }),
      });

      const data = (await response.json()) as QueryResponse | { detail?: string };
      if (!response.ok) {
        throw new Error((data as { detail?: string }).detail || "Query failed");
      }

      const typed = data as QueryResponse;
      setPreviousResponseId(typed.response_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: typed.answer,
          citations: typed.citations || [],
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          text: error instanceof Error ? error.message : "Something went wrong",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative mx-auto flex h-[100dvh] w-full max-w-5xl flex-col px-4 py-6 sm:px-6">
      {!isUnlocked && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-2xl border bg-[var(--surface)] p-6 shadow-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Protected Demo
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--primary)]">
              Enter password to continue
            </h2>
            <p className="mt-2 text-sm text-[var(--muted)]">
              This chat is locked. You cannot access messages until authentication succeeds.
            </p>
            <form className="mt-4 space-y-3" onSubmit={onUnlock}>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Demo password"
                className="h-11 w-full rounded-xl border bg-white px-3 text-sm outline-none ring-[var(--accent)] transition focus:ring-2"
              />
              {authError && <p className="text-sm text-[var(--error)]">{authError}</p>}
              <button
                type="submit"
                disabled={authLoading}
                className="h-11 w-full rounded-xl bg-[var(--accent)] px-4 text-sm font-semibold text-white transition enabled:hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {authLoading ? "Checking..." : "Unlock Chat"}
              </button>
            </form>
          </div>
        </div>
      )}

      <section className="mb-4 rounded-2xl border bg-[var(--surface)] p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          Public Demo Chat
        </p>
        <div className="mt-2 flex items-center gap-3">
          {logoUrl ? (
            <Image
              src={logoUrl}
              alt={`${demoName} logo`}
              width={36}
              height={36}
              className="h-9 w-9 rounded-md border bg-white object-contain p-1"
            />
          ) : null}
          <h1 className="text-2xl font-semibold text-[var(--primary)]">{demoName}</h1>
        </div>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Provide password if set, then ask questions.
        </p>
      </section>

      <section className="flex min-h-0 flex-1 flex-col rounded-2xl border bg-[var(--surface)] shadow-sm">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className="space-y-2">
              <div
                className={[
                  "max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-6",
                  message.role === "user"
                    ? "ml-auto bg-[var(--primary)] text-white"
                    : message.role === "error"
                      ? "bg-red-50 text-[var(--error)]"
                      : "bg-[#efe6d6] text-[var(--foreground)]",
                ].join(" ")}
              >
                {message.role === "assistant" ? (
                  <div className="prose prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-1">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
                  </div>
                ) : (
                  message.text
                )}
              </div>
              {message.role === "assistant" && !!message.citations?.length && (
                <div className="max-w-[90%] rounded-xl border bg-white/70 p-3 text-xs text-[var(--muted)]">
                  <p className="mb-2 font-semibold uppercase tracking-[0.12em]">Citations</p>
                  <div className="space-y-1">
                    {message.citations.map((citation, citationIndex) => (
                      <p key={`${citationLabel(citation)}-${citationIndex}`}>
                        [{citation.number ?? citationIndex + 1}] {citationLabel(citation)}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="max-w-[90%] rounded-2xl bg-[#efe6d6] px-4 py-3 text-sm text-[var(--muted)]">
              Thinking...
            </div>
          )}
        </div>

        <form className="border-t bg-[#fbf7ee] p-4" onSubmit={onSubmit}>
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <input
              type="text"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question..."
              disabled={!isUnlocked}
              className="h-11 rounded-xl border bg-white px-3 text-sm outline-none ring-[var(--accent)] transition focus:ring-2"
            />
            <button
              type="submit"
              disabled={!isUnlocked || loading || !question.trim()}
              className="h-11 rounded-xl bg-[var(--accent)] px-4 text-sm font-semibold text-white transition enabled:hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Sending..." : "Send"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
