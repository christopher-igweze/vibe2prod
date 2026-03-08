import Link from "next/link";

export const dynamic = "force-dynamic";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background text-foreground">
      <h1 className="text-6xl font-bold forge-gradient-text">404</h1>
      <p className="mt-4 text-lg text-[#8692A8]">Page not found</p>
      <Link
        href="/"
        className="mt-8 rounded-lg bg-forge-emerald px-6 py-2.5 text-sm font-semibold text-[#0B0F19] hover:bg-emerald-400 transition-colors"
      >
        Go Home
      </Link>
    </div>
  );
}
