import Link from "next/link";
import { SearchBar } from "@/components/SearchBar";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <main className="flex flex-col items-center gap-8 text-center px-8 w-full">
        <h1 className="text-4xl font-semibold tracking-tight">
          Explore the Universe
        </h1>
        <p className="text-lg text-zinc-400 max-w-md">
          Interactive sky viewer for JWST imagery. Search for objects by name,
          coordinates, or type, or navigate directly to an observation.
        </p>

        <SearchBar />

        <nav className="flex gap-4 text-sm">
          <Link
            href="/dashboard"
            className="rounded bg-zinc-800 px-4 py-2 font-medium hover:bg-zinc-700"
          >
            Pipeline dashboard
          </Link>
        </nav>
      </main>
    </div>
  );
}
