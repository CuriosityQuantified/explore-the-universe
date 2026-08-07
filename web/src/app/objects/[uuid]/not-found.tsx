import Link from "next/link";

export default function ObjectNotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-semibold">Object Not Found</h1>
        <p className="text-zinc-400">
          The requested astronomical object does not exist or has not been processed yet.
        </p>
        <Link href="/" className="text-sm text-blue-400 hover:underline">
          ← Back to home
        </Link>
      </div>
    </div>
  );
}
