"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
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
  company_url: string;
  logo_url?: string | null;
  expires_at?: string;
};

type Message = {
  role: "user" | "assistant" | "error";
  text: string;
  citations?: Citation[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000";

const EXAMPLE_PROMPTS = [
  "What does this company do?",
  "Summarize the indexed website",
  "What services are covered?",
];

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
  const [companyUrl, setCompanyUrl] = useState("");
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [previousResponseId, setPreviousResponseId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const endpoint = useMemo(() => `${API_BASE_URL}/api/v1/demos/${slug}/query`, [slug]);
  const authEndpoint = useMemo(() => `${API_BASE_URL}/api/v1/demos/${slug}/auth`, [slug]);
  const demoMetaEndpoint = useMemo(() => `${API_BASE_URL}/api/v1/demos/${slug}`, [slug]);
  const hasMessages = messages.length > 0;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    let active = true;

    async function loadDemoMeta() {
      try {
        const response = await fetch(demoMetaEndpoint, { method: "GET" });
        if (!response.ok) return;
        const data = (await response.json()) as DemoMetaResponse;
        if (!active) return;
        setDemoName(data.prospect_name || "Demo Chat");
        setCompanyUrl(data.company_url || "");
        setLogoUrl(data.logo_url || null);
      } catch {
        // Metadata failure should not block password access.
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
          if (!data.requires_password && data.authenticated) setIsUnlocked(true);
          return;
        }
        if (response.status === 401) return;
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

      setIsUnlocked((data as AuthResponse).authenticated);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setAuthLoading(false);
    }
  }

  async function submitPrompt(prompt: string) {
    if (!isUnlocked) return;
    const trimmed = prompt.trim();
    if (!trimmed || loading) return;

    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setLoading(true);

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmed,
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

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitPrompt(question);
  }

  return (
    <main className="relative min-h-[100dvh] overflow-hidden bg-[#202020] text-[#f4f4f4]">
      {!isUnlocked && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/70 px-4 backdrop-blur-md">
          <div className="w-full max-w-md rounded-3xl border border-white/10 bg-[#2b2b2b] p-6 shadow-2xl">
            <div className="mb-5 flex items-center gap-3">
              <LogoMark logoUrl={logoUrl} demoName={demoName} />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/45">
                  Protected Demo
                </p>
                <h2 className="text-2xl font-semibold tracking-tight text-white">{demoName}</h2>
              </div>
            </div>
            <p className="text-sm leading-6 text-white/65">
              Enter the demo password shared with this link. The chat stays locked until the password is correct.
            </p>
            <form className="mt-5 space-y-3" onSubmit={onUnlock}>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Demo password"
                autoFocus
                className="h-12 w-full rounded-2xl border border-white/10 bg-[#1f1f1f] px-4 text-sm text-white outline-none transition placeholder:text-white/35 focus:border-white/25"
              />
              {authError && (
                <p className="rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-200">
                  {authError}
                </p>
              )}
              <button
                type="submit"
                disabled={authLoading || !password.trim()}
                className="h-12 w-full rounded-2xl bg-white px-4 text-sm font-semibold text-[#202020] transition enabled:hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {authLoading ? "Checking..." : "Unlock chat"}
              </button>
            </form>
          </div>
        </div>
      )}

      <header className="absolute left-0 right-0 top-0 z-10 flex h-16 items-center justify-between px-5">
        <div className="flex min-w-0 items-center gap-3">
          <LogoMark logoUrl={logoUrl} demoName={demoName} compact />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{demoName}</p>
            {companyUrl && (
              <a
                href={companyUrl}
                target="_blank"
                rel="noreferrer"
                className="block max-w-[220px] truncate text-xs text-white/45 hover:text-white/70"
              >
                {companyUrl.replace(/^https?:\/\//, "")}
              </a>
            )}
          </div>
        </div>
        <div className="rounded-full border border-white/10 px-3 py-1 text-xs font-medium text-white/50">
          Demo
        </div>
      </header>

      <section
        className={[
          "mx-auto flex min-h-[100dvh] w-full max-w-4xl flex-col px-4 pb-5 pt-20 transition-all sm:px-6",
          hasMessages ? "justify-end" : "justify-center",
        ].join(" ")}
      >
        {!hasMessages && (
          <div className="mx-auto mb-8 w-full max-w-3xl text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Where should we begin?
            </h1>
          </div>
        )}

        {hasMessages && (
          <div
            ref={scrollRef}
            className="mx-auto mb-4 max-h-[calc(100dvh-10rem)] w-full max-w-3xl space-y-6 overflow-y-auto py-2"
          >
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
              >
                <div
                  className={[
                    "space-y-2",
                    message.role === "user" ? "max-w-[88%] sm:max-w-[76%]" : "w-full",
                  ].join(" ")}
                >
                  <div
                    className={[
                      "rounded-3xl px-5 py-3 text-sm leading-7",
                      message.role === "user"
                        ? "bg-[#303030] text-white"
                        : message.role === "error"
                          ? "bg-red-500/10 text-red-200"
                          : "bg-transparent text-white/90",
                    ].join(" ")}
                  >
                    {message.role === "assistant" ? (
                      <div className="markdown-content dark-markdown">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
                      </div>
                    ) : (
                      message.text
                    )}
                  </div>

                  {message.role === "assistant" && !!message.citations?.length && (
                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3 text-xs text-white/55">
                      <p className="mb-2 font-semibold uppercase tracking-[0.14em] text-white/75">
                        Citations
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {message.citations.map((citation, citationIndex) => (
                          <span
                            key={`${citationLabel(citation)}-${citationIndex}`}
                            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1"
                          >
                            [{citation.number ?? citationIndex + 1}] {citationLabel(citation)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="text-sm text-white/50">Searching sources...</div>
            )}
          </div>
        )}

        <form className="mx-auto w-full max-w-3xl" onSubmit={onSubmit}>
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-[#303030] p-2 shadow-2xl">
            <button
              type="button"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-2xl font-light text-white/75 transition hover:bg-white/10"
              aria-label="Add context"
            >
              +
            </button>
            <input
              type="text"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask anything"
              disabled={!isUnlocked}
              className="h-10 min-w-0 flex-1 bg-transparent px-1 text-sm font-medium text-white outline-none placeholder:text-white/45 disabled:cursor-not-allowed disabled:opacity-60"
            />
            <button
              type="button"
              className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/70 transition hover:bg-white/10 sm:flex"
              aria-label="Voice input"
            >
              ◌
            </button>
            <button
              type="submit"
              disabled={!isUnlocked || loading || !question.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#0b7cff] text-sm font-bold text-white transition enabled:hover:bg-[#1d86ff] disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/35"
              aria-label="Send message"
            >
              {loading ? <BouncingDots /> : "↑"}
            </button>
          </div>
        </form>

        {!hasMessages && (
          <div className="mx-auto mt-5 flex w-full max-w-3xl flex-wrap justify-center gap-3">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                disabled={!isUnlocked || loading}
                onClick={() => void submitPrompt(prompt)}
                className="rounded-full border border-white/10 bg-transparent px-4 py-2 text-sm font-semibold text-white/85 transition enabled:hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function BouncingDots() {
  return (
    <span className="flex items-center gap-0.5" aria-label="Thinking">
      <span className="h-1 w-1 animate-bounce rounded-full bg-white/80 [animation-delay:-0.24s]" />
      <span className="h-1 w-1 animate-bounce rounded-full bg-white/80 [animation-delay:-0.12s]" />
      <span className="h-1 w-1 animate-bounce rounded-full bg-white/80" />
    </span>
  );
}

function LogoMark({
  logoUrl,
  demoName,
  compact = false,
}: {
  logoUrl: string | null;
  demoName: string;
  compact?: boolean;
}) {
  const size = compact ? "h-8 w-8" : "h-11 w-11";

  if (logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={logoUrl}
        alt={`${demoName} logo`}
        className={`${size} shrink-0 rounded-xl border border-white/10 bg-white object-contain p-1.5`}
      />
    );
  }

  return (
    <div
      className={`${size} flex shrink-0 items-center justify-center rounded-xl bg-white text-xs font-bold uppercase text-[#202020]`}
    >
      {demoName.slice(0, 2)}
    </div>
  );
}
