"use client";

import { Component, type ReactNode } from "react";

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
        <section className="card">
          <div className="notice">
            <strong>Something went wrong</strong>
            <p>{this.state.message || "An unexpected error occurred."}</p>
            <button
              className="secondary-button"
              onClick={() => this.setState({ hasError: false, message: "" })}
            >
              Try again
            </button>
          </div>
        </section>
      );
    }
    return this.props.children;
  }
}
