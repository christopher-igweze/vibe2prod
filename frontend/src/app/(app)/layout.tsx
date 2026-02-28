import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-neutral-950">
      <nav className="border-b border-neutral-800 bg-neutral-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-3">
          <Link href="/" className="text-lg font-bold tracking-tight">
            <span className="text-emerald-400">Vibe</span>
            <span className="text-neutral-100">2Prod</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/scan/new"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              New Scan
            </Link>
            <Link
              href="/settings"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              Settings
            </Link>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: "h-8 w-8",
                },
              }}
            />
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
