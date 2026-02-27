import React from 'react';

function FactCheckCard({ title, url, source }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Read fact-check: ${title}`}
      className="block bg-purple-900/20 hover:bg-purple-900/40 border border-purple-800 hover:border-purple-600
                 rounded-xl p-4 transition-all duration-200 group"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-purple-200 group-hover:text-white line-clamp-2 leading-snug">
            {title || 'Fact Check'}
          </p>
          {source && (
            <span className="inline-block mt-2 text-xs text-purple-400 bg-purple-900/50 px-2 py-0.5 rounded-full">
              {source}
            </span>
          )}
        </div>
        <svg className="h-4 w-4 text-purple-600 group-hover:text-purple-400 flex-shrink-0 mt-0.5 transition-colors"
             fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </div>
    </a>
  );
}

export default function FactChecks({ factChecks }) {
  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
        <span>🔍</span> Fact-Check Results
      </h3>
      {!factChecks || factChecks.length === 0 ? (
        <p className="text-gray-500 text-sm">No fact-check results found.</p>
      ) : (
        <div className="space-y-3">
          {factChecks.map((fc, idx) => (
            <FactCheckCard key={idx} {...fc} />
          ))}
        </div>
      )}
    </div>
  );
}
