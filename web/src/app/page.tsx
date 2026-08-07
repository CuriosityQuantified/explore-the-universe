import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <main className="flex flex-col items-center gap-6 text-center px-8">
        <h1 className="text-4xl font-semibold tracking-tight">
          Explore the Universe
        </h1>
        <p className="text-lg text-zinc-400 max-w-md">
          Interactive sky viewer for JWST imagery. Navigate to{" "}
          <code className="text-sm bg-zinc-800 px-2 py-1 rounded font-mono">
            /viewer/[uuid]
          </code>{" "}
          with an observation UUID to begin exploring.
        </p>
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
