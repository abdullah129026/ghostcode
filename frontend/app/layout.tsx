import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://ghostcode-shah20.vercel.app"),
  title: "GhostCode: turns dead code into a P&L statement",
  description:
    "GhostCode maps your repository's dependency graph, finds the code nothing calls, and prices it in dollars per year.",
  openGraph: {
    title: "GhostCode: turns dead code into a P&L statement",
    description:
      "Upload any GitHub repo. Get a dependency graph, dead code priced in dollars per year, and safe auto-generated deletion PRs.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "GhostCode: turns dead code into a P&L statement",
    description:
      "Upload any GitHub repo. Get a dependency graph, dead code priced in dollars per year, and safe auto-generated deletion PRs.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        {children}
      </body>
    </html>
  );
}
