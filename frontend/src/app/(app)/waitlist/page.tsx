import { Clock } from "lucide-react"

export default function WaitlistPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-6">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-500/15 mb-6">
        <Clock className="size-8 text-amber-400" />
      </div>
      <h1 className="text-3xl font-bold text-neutral-100 mb-3">
        You&apos;re on the waitlist
      </h1>
      <p className="text-neutral-400 text-lg max-w-md mb-2">
        We&apos;re rolling out access in waves. You&apos;ll get an email when your spot is ready.
      </p>
      <p className="text-neutral-500 text-sm">
        Follow us on{" "}
        <a
          href="https://x.com/vibe2prod"
          target="_blank"
          rel="noopener noreferrer"
          className="text-emerald-400 hover:text-emerald-300 underline"
        >
          X
        </a>{" "}
        for updates.
      </p>
    </div>
  )
}
