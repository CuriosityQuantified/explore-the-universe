import Link from "next/link";
import { SearchBar } from "@/components/SearchBar";
import { CatalogSummary } from "@/components/CatalogSummary";

export default function Home() {
  return (
    <div className="flex min-h-screen justify-center">
      <main className="flex flex-col items-center gap-6 text-center px-3 py-10 sm:px-8 w-full">
        <h1 className="text-4xl font-semibold tracking-tight">
          Explore the Universe
        </h1>
        <p className="text-lg text-zinc-400 max-w-md">
          Explore galaxies, nebulae, and star clusters in survey and JWST imagery. Search by name,
          coordinates, or type, or browse the complete object catalog below.
        </p>

        <SearchBar />
        <p className="text-sm text-zinc-400">Try M31, M42, M45, or NGC 253.</p>
        <CatalogSummary />

        <nav className="flex gap-4 text-sm">
          <Link
            href="/dashboard"
            className="rounded bg-zinc-800 px-4 py-2 font-medium hover:bg-zinc-700"
          >
            Pipeline dashboard
          </Link>
          <Link
            href="/chat"
            className="rounded bg-zinc-800 px-4 py-2 font-medium hover:bg-zinc-700"
          >
            AI Chat
          </Link>
        </nav>
      </main>
    </div>
  );
}
