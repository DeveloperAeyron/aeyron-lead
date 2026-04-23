import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Lead Radar — Spawn Radius Scraper Dashboard",
  description:
    "Real-time lead discovery dashboard powered by spawn-radius-scraper. Find and export business leads from Google Maps.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full flex font-sans">
        <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem>
          <Sidebar />
          <main className="flex-1 overflow-y-auto h-screen scrollbar-thin relative">
            {children}
          </main>
        </ThemeProvider>
      </body>
    </html>
  );
}
