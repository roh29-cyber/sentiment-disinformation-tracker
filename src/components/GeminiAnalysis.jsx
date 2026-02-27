import React, { useState } from 'react';

const VERDICT_STYLES = {
  'FALSE':          { bg: 'bg-red-900/40', border: 'border-red-600', text: 'text-red-300', icon: '✗', badge: 'bg-red-800 text-red-200' },
  'MISLEADING':     { bg: 'bg-orange-900/40', border: 'border-orange-600', text: 'text-orange-300', icon: '⚠', badge: 'bg-orange-800 text-orange-200' },
  'PARTIALLY TRUE': { bg: 'bg-yellow-900/40', border: 'border-yellow-600', text: 'text-yellow-300', icon: '◐', badge: 'bg-yellow-800 text-yellow-200' },
  'UNVERIFIED':     { bg: 'bg-gray-800/60', border: 'border-gray-600', text: 'text-gray-300', icon: '?', badge: 'bg-gray-700 text-gray-300' },
  'TRUE':           { bg: 'bg-green-900/40', border: 'border-green-600', text: 'text-green-300', icon: '✓', badge: 'bg-green-800 text-green-200' },
};

function getVerdictStyle(verdict) {
  const upper = (verdict || '').toUpperCase().trim();
  for (const [key, style] of Object.entries(VERDICT_STYLES)) {
    if (upper.includes(key)) return style;
  }
  return VERDICT_STYLES['UNVERIFIED'];
}

export default function GeminiAnalysis({ geminiData }) {
  const [showRaw, setShowRaw] = useState(false);

  if (!geminiData) return null;

  const style = getVerdictStyle(geminiData.verdict);

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
          <span>🤖</span> AI Analysis
          <span className="text-[10px] font-normal text-gray-500 bg-gray-900 px-2 py-0.5 rounded-full border border-gray-700">
            Powered by Gemini
          </span>
        </h3>
      </div>

      {/* Verdict Badge */}
      {geminiData.verdict && (
        <div className={`${style.bg} border ${style.border} rounded-xl p-4 mb-4`}>
          <div className="flex items-center gap-3">
            <span className={`text-2xl ${style.text}`}>{style.icon}</span>
            <div>
              <span className={`text-xs font-semibold uppercase tracking-wide ${style.text}`}>
                AI Verdict
              </span>
              <p className={`text-lg font-bold ${style.text}`}>
                {geminiData.verdict}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Analysis */}
      {geminiData.analysis && (
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <span>📊</span> Analysis
          </h4>
          <p className="text-sm text-gray-300 leading-relaxed bg-gray-900/50 border border-gray-700 rounded-lg p-3">
            {geminiData.analysis}
          </p>
        </div>
      )}

      {/* Key Facts */}
      {geminiData.key_facts && geminiData.key_facts.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <span>📌</span> Key Facts
          </h4>
          <ul className="space-y-1.5">
            {geminiData.key_facts.map((fact, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="text-blue-400 mt-0.5 flex-shrink-0">•</span>
                <span className="leading-relaxed">{fact}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendation */}
      {geminiData.recommendation && (
        <div className="bg-blue-900/20 border border-blue-800 rounded-xl p-3 mb-3">
          <div className="flex items-start gap-2">
            <span className="text-blue-400 text-sm mt-0.5">💡</span>
            <p className="text-sm text-blue-200 leading-relaxed">
              {geminiData.recommendation}
            </p>
          </div>
        </div>
      )}

      {/* Raw response toggle */}
      {geminiData.raw_response && (
        <div>
          <button
            onClick={() => setShowRaw(!showRaw)}
            className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
          >
            <svg
              className={`w-3 h-3 transform transition-transform ${showRaw ? 'rotate-90' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            {showRaw ? 'Hide' : 'Show'} raw AI response
          </button>
          {showRaw && (
            <pre className="mt-2 text-xs text-gray-500 bg-gray-900 border border-gray-700 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap max-h-60 overflow-y-auto">
              {geminiData.raw_response}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
