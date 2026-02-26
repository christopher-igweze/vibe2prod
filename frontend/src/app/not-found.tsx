import Link from "next/link";

export const dynamic = "force-dynamic";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-neutral-950 text-neutral-100">
      <h1 className="text-6xl font-bold text-emerald-400">404</h1>
      <p className="mt-4 text-lg text-neutral-400">Page not found</p>
      <Link
        href="/"
        className="mt-8 rounded-lg bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-neutral-950 hover:bg-emerald-400 transition-colors"
      >
        Go Home
      </Link>
    </div>
  );
}
