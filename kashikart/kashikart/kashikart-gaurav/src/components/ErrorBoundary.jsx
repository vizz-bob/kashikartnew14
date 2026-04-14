import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught an error:", error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (typeof this.props.onReset === "function") {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      const showDetails =
        typeof this.props.showDetails === "boolean"
          ? this.props.showDetails
          : import.meta?.env?.DEV;
      const fullScreen =
        typeof this.props.fullScreen === "boolean" ? this.props.fullScreen : true;
      const title = this.props.title || "Something went wrong";
      const message =
        this.props.message ||
        "Please try again. If the problem continues, contact support.";
      const showReload =
        typeof this.props.showReload === "boolean" ? this.props.showReload : true;

      return (
        <div
          className={
            fullScreen
              ? "flex min-h-screen items-center justify-center bg-[#F8FAFC] px-6 py-10"
              : "flex w-full items-center justify-center px-6 py-10"
          }
        >
          <div className="w-full max-w-xl rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
            <p className="mt-2 text-sm text-slate-600">{message}</p>
            {showDetails && this.state.error ? (
              <pre className="mt-4 overflow-auto rounded bg-slate-50 p-3 text-left text-xs text-slate-700">
                {this.state.error.message}
              </pre>
            ) : null}
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <button
                type="button"
                onClick={this.handleReset}
                className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                Try again
              </button>
              {showReload ? (
                <button
                  type="button"
                  onClick={() => window.location.reload()}
                  className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Reload page
                </button>
              ) : null}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
