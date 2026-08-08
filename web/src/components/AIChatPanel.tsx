"use client";

import Image from "next/image";
import Link from "next/link";
import { useRef, useState } from "react";

import { chatQuery } from "@/lib/api";
import type { ChatMessage, ChatObjectResult } from "@/types/chat";

// ---------------------------------------------------------------------------
// Object card shown inline below assistant messages
// ---------------------------------------------------------------------------

function ObjectCard({ obj }: { obj: ChatObjectResult }) {
  return (
    <Link
      href={obj.detail_url}
      className="flex flex-col gap-1 rounded-lg bg-zinc-800 p-3 min-w-[140px] max-w-[160px] hover:bg-zinc-700 transition-colors flex-shrink-0"
    >
      {obj.thumbnail_url ? (
        <div className="relative w-full aspect-square rounded overflow-hidden bg-zinc-900">
          <Image
            src={obj.thumbnail_url}
            alt={obj.catalog_name ?? obj.type ?? "Astronomical object"}
            fill
            className="object-cover"
            unoptimized
          />
        </div>
      ) : (
        <div className="w-full aspect-square rounded bg-zinc-900 flex items-center justify-center text-zinc-500 text-xs">
          No image
        </div>
      )}
      <p className="text-xs font-medium text-zinc-200 truncate">
        {obj.catalog_name ?? obj.uuid.slice(0, 8)}
      </p>
      {obj.type && (
        <p className="text-xs text-zinc-400 truncate">{obj.type}</p>
      )}
    </Link>
  );
}

// ---------------------------------------------------------------------------
// A single message bubble
// ---------------------------------------------------------------------------

function MessageBubble({
  message,
  showQueryMap,
  onToggleQuery,
  index,
}: {
  message: ChatMessage;
  showQueryMap: Record<number, boolean>;
  onToggleQuery: (idx: number) => void;
  index: number;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`rounded-2xl px-4 py-2 max-w-prose text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-600 text-white rounded-br-sm"
            : "bg-zinc-800 text-zinc-100 rounded-bl-sm"
        }`}
      >
        {message.content}
      </div>

      {/* Inline object thumbnails for assistant messages */}
      {!isUser && message.objects && message.objects.length > 0 && (
        <div
          className="flex gap-3 overflow-x-auto pb-2 max-w-full"
          aria-label="Matching astronomical objects"
        >
          {message.objects.map((obj) => (
            <ObjectCard key={obj.uuid} obj={obj} />
          ))}
        </div>
      )}

      {/* Show query toggle for assistant messages with an executed query */}
      {!isUser && message.query_executed != null && (
        <div className="text-xs">
          <button
            onClick={() => onToggleQuery(index)}
            className="text-zinc-400 hover:text-zinc-200 underline underline-offset-2"
            aria-expanded={showQueryMap[index] ?? false}
          >
            {showQueryMap[index] ? "Hide query" : "Show query"}
          </button>
          {showQueryMap[index] && (
            <pre className="mt-1 rounded bg-zinc-900 p-3 text-zinc-300 overflow-x-auto text-xs leading-relaxed">
              {JSON.stringify(message.query_executed, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main AIChatPanel
// ---------------------------------------------------------------------------

interface AIChatPanelProps {
  /** Pre-scope all queries to this observation UUID */
  defaultObservationUuid?: string;
}

export function AIChatPanel({ defaultObservationUuid }: AIChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [observationUuid, setObservationUuid] = useState(defaultObservationUuid ?? "");
  const [showQueryMap, setShowQueryMap] = useState<Record<number, boolean>>({});

  const bottomRef = useRef<HTMLDivElement>(null);

  function toggleQuery(index: number) {
    setShowQueryMap((prev) => ({ ...prev, [index]: !prev[index] }));
  }

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const data = await chatQuery(trimmed, observationUuid || undefined);
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: data.answer,
        objects: data.objects,
        query_executed: data.query_executed,
      };
      setMessages([...nextMessages, assistantMessage]);
      // Scroll to bottom on next tick
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Context selector */}
      <div className="px-4 py-2 border-b border-zinc-800">
        <label className="flex items-center gap-2 text-xs text-zinc-400">
          <span className="flex-shrink-0">Observation UUID (optional):</span>
          <input
            type="text"
            value={observationUuid}
            onChange={(e) => setObservationUuid(e.target.value)}
            placeholder="Scope to an observation…"
            className="flex-1 bg-zinc-900 rounded px-2 py-1 text-zinc-200 placeholder:text-zinc-600 text-xs outline-none focus:ring-1 focus:ring-indigo-500 min-w-0"
            aria-label="Observation UUID context selector"
          />
        </label>
      </div>

      {/* Message history */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 min-h-0">
        {messages.length === 0 && (
          <p className="text-zinc-500 text-sm text-center mt-8">
            Ask a question about the astronomical catalog.
            <br />
            <span className="text-zinc-600">
              e.g. &ldquo;Show me the five brightest anomaly-flagged galaxies&rdquo;
            </span>
          </p>
        )}
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            index={i}
            message={msg}
            showQueryMap={showQueryMap}
            onToggleQuery={toggleQuery}
          />
        ))}
        {loading && (
          <div className="flex items-start">
            <div className="rounded-2xl rounded-bl-sm bg-zinc-800 px-4 py-2 text-sm text-zinc-400">
              Thinking…
            </div>
          </div>
        )}
        {error && (
          <div className="rounded bg-red-900/40 border border-red-700 px-4 py-2 text-sm text-red-300">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-zinc-800 p-4 flex gap-2 items-end">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about the catalog… (Enter to send, Shift+Enter for newline)"
          rows={2}
          maxLength={2000}
          disabled={loading}
          className="flex-1 resize-none rounded-lg bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
          aria-label="Chat message input"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          aria-label="Send message"
        >
          Send
        </button>
      </div>
    </div>
  );
}
