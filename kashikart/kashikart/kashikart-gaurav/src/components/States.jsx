import React, { memo } from "react";

export const LoadingState = memo(function LoadingState({
  message = "Loading...",
}) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-500">
      <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
      {message}
    </div>
  );
});

export const ErrorState = memo(function ErrorState({
  message = "Something went wrong.",
  onRetry,
  className = "",
}) {
  return (
    <div
      className={`rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 ${className}`}
    >
      <div>{message}</div>
      {typeof onRetry === "function" ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex items-center rounded border border-red-200 bg-white px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
});

export const EmptyState = memo(function EmptyState({
  title = "No data found",
  message = "There is nothing to show right now.",
  className = "",
}) {
  return (
    <div
      className={`rounded-lg border border-dashed border-gray-200 bg-white px-6 py-8 text-center ${className}`}
    >
      <div className="text-sm font-semibold text-gray-800">{title}</div>
      <div className="mt-2 text-xs text-gray-500">{message}</div>
    </div>
  );
});
