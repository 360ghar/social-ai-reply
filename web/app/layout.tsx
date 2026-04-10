import type { Metadata } from "next";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";

import "../styles/globals.css";
import { AuthProvider } from "../components/auth/auth-provider";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "RedditFlow",
  description:
    "AI visibility, community engagement, and content workflows for brands building authority across modern discovery channels.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={cn(inter.variable)}>
      <body>
        <ThemeProvider
          attribute="data-theme"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
          storageKey="rf-theme"
        >
          <ErrorBoundary>
            <AuthProvider>
              <TooltipProvider>
                {children}
                <Toaster richColors position="bottom-right" />
              </TooltipProvider>
            </AuthProvider>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
