import Link from "next/link";

import { AIChatPanel } from "@/components/AIChatPanel";

export const metadata = {
  title: "AI Chat — Explore the Universe",
  description: "Ask natural-language questions about the astronomical catalog.",
};

export default function ChatPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Page header / nav */}
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-4">
        <Link href="/" className="text-zinc-400 hover:text-zinc-200 text-sm">
          ← Home
        </Link>
        <h1 className="text-sm font-semibold text-zinc-200">AI Chat</h1>
        <span className="text-xs text-zinc-500 ml-auto">
          Powered by Claude · catalog queries only
        </span>
      </header>

      {/* Chat panel fills remaining height */}
      <div className="flex-1 min-h-0">
        <AIChatPanel />
      </div>
    </div>
  );
}
