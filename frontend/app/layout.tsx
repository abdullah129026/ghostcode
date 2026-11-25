import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import DotField from "@/components/DotField";

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

// Runs before hydration so the first paint already has the right theme
// and there is no light/dark flash. Stored choice wins, else the OS.
const themeScript = `(function(){try{var t=localStorage.getItem("ghostcode-theme");if(t==="dark"||(!t&&window.matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.add("dark")}}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <DotField />
        {children}
      </body>
    </html>
  );
}
