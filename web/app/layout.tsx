import type { Metadata } from "next";
import { Merriweather, Space_Grotesk } from "next/font/google";

import "./globals.css";
import { AuthProvider } from "../components/auth-provider";

const sans = Space_Grotesk({ subsets: ["latin"], variable: "--font-sans" });
const serif = Merriweather({ subsets: ["latin"], variable: "--font-serif", weight: ["400", "700"] });

export const metadata: Metadata = {
  title: "RedditFlow",
  description: "Simple Reddit lead finding and reply drafting for growing businesses."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
