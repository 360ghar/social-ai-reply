import type { Metadata } from "next";

import "../styles/globals.css";
import "../styles/components.css";
import "../styles/layout.css";
import "../styles/pages.css";
import "../styles/utilities.css";
import { AuthProvider } from "../components/auth-provider";

export const metadata: Metadata = {
  title: "RedditFlow",
  description: "AI visibility, community engagement, and content workflows for brands building authority across modern discovery channels."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
