import React, { useState } from 'react';

export default function InputForm({ onAnalyze, loading }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onAnalyze(input.trim());
    }
  };

  const examples = [
    { label: 'URL', value: 'https://www.bbc.com/news' },
    { label: 'Topic', value: 'climate change misinformation' },
    { label: 'Keyword', value: 'election fraud claims 2024' },
  ];

  return (
    <div className="w-full max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter a URL (https://example.com) or a topic/keyword to analyze..."
            rows={3}
            aria-label="Input URL or topic"
            className="w-full bg-gray-800 border border-gray-700 rounded-2xl px-5 py-4 text-gray-100
                       placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand
                       resize-none text-sm leading-relaxed transition-all"
          />
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs text-gray-500">Try:</span>
          {examples.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => setInput(ex.value)}
              className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700
                         text-gray-400 hover:text-gray-200 px-3 py-1 rounded-full transition-colors"
            >
              {ex.label}: <span className="text-brand">{ex.value.slice(0, 30)}{ex.value.length > 30 ? '…' : ''}</span>
            </button>
          ))}
        </div>

        <button
          type="submit"
          disabled={loading || !input.trim()}
          aria-label="Analyze input"
          className="self-end bg-brand hover:bg-brand-dark disabled:opacity-50 disabled:cursor-not-allowed
                     text-white font-semibold px-8 py-3 rounded-xl transition-all duration-200
                     flex items-center gap-2 shadow-lg shadow-brand/20"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Analyzing…
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Analyze
            </>
          )}
        </button>
      </form>
    </div>
  );
}
