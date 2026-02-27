import React from 'react';

export default function ErrorAlert({ error, onDismiss }) {
  return (
    <div
      role="alert"
      className="bg-red-900/30 border border-red-700 rounded-2xl p-5 flex items-start gap-4"
    >
      <span className="text-2xl flex-shrink-0" aria-hidden="true">❌</span>
      <div className="flex-1">
        <h3 className="text-red-400 font-semibold mb-1">Analysis Failed</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="text-red-500 hover:text-red-300 transition-colors flex-shrink-0"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}
