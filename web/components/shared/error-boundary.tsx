"use client";

import { Component, type ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type Props = { children: ReactNode };
type State = { hasError: boolean; message: string };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <Card className="mx-auto mt-8 max-w-md">
          <CardContent className="flex flex-col gap-3 pt-6">
            <strong className="text-base font-semibold text-foreground">Something went wrong</strong>
            <p className="text-sm text-muted-foreground">
              {this.state.message || "An unexpected error occurred."}
            </p>
            <Button
              variant="outline"
              onClick={() => this.setState({ hasError: false, message: "" })}
            >
              Try again
            </Button>
          </CardContent>
        </Card>
      );
    }
    return this.props.children;
  }
}
