import { SignIn } from "@clerk/nextjs";

export const dynamic = "force-dynamic";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-950">
      <SignIn
        forceRedirectUrl="/dashboard"
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "bg-neutral-900 border border-neutral-800",
          },
        }}
      />
    </div>
  );
}
