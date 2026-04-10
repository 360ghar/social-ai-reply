import AppShell from "@/components/app/app-shell";
import { ErrorBoundary } from "@/components/shared/error-boundary";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return <AppShell><ErrorBoundary>{children}</ErrorBoundary></AppShell>;
}
