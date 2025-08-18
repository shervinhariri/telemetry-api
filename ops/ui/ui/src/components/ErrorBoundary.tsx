import React from "react";

type State = { hasError: boolean; message?: string };

export class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  state: State = { hasError: false };
  static getDerivedStateFromError(e: Error) { return { hasError: true, message: e.message }; }
  componentDidCatch(err: Error, info: React.ErrorInfo) { console.error("UI ErrorBoundary:", err, info); }
  render() {
    if (this.state.hasError) {
      return <div className="p-4 text-sm text-red-300">Something went wrong in the UI. Try refresh.</div>;
    }
    return this.props.children;
  }
}


