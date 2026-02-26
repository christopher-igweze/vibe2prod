import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Vibe2Prod — Ship AI Code With Confidence",
  description:
    "Audit your AI-generated codebase in minutes. Get actionable security, reliability, and scalability findings with context-aware prioritization.",
  openGraph: {
    title: "Vibe2Prod — Ship AI Code With Confidence",
    description:
      "Audit your AI-generated codebase in minutes. Get actionable findings prioritized for your project stage.",
    url: "https://vibe2prod.com",
    siteName: "Vibe2Prod",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Vibe2Prod — Ship AI Code With Confidence",
    description:
      "Audit your AI-generated codebase in minutes. Get actionable findings prioritized for your project stage.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInForceRedirectUrl="/dashboard"
      signUpForceRedirectUrl="/dashboard"
    >
      <html lang="en" className="dark">
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased bg-neutral-950 text-neutral-100`}
        >
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
