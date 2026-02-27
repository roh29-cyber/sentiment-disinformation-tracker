import React, { useState } from 'react';

const VERDICT_CONFIG = {
  likely_false: {
    label: 'Likely False',
    color: 'red',
    icon: '✗',
    bg: 'bg-red-900/30',
    border: 'border-red-700',
    text: 'text-red-300',
    badge: 'bg-red-900/60 text-red-200',
  },
  likely_true: {
    label: 'Likely True',
    color: 'green',
    icon: '✓',
    bg: 'bg-green-900/30',
    border: 'border-green-700',
    text: 'text-green-300',
    badge: 'bg-green-900/60 text-green-200',
  },
  disputed: {
    label: 'Disputed',
    color: 'yellow',
    icon: '⚠',
    bg: 'bg-yellow-900/30',
    border: 'border-yellow-700',
    text: 'text-yellow-300',
    badge: 'bg-yellow-900/60 text-yellow-200',
  },
  unverified: {
    label: 'Unverified',
    color: 'gray',
    icon: '?',
    bg: 'bg-gray-800/50',
    border: 'border-gray-600',
    text: 'text-gray-400',
    badge: 'bg-gray-700 text-gray-300',
  },
};

const RELIABILITY_CONFIG = {
  reliable: { label: 'Reliable', color: 'text-green-400', bg: 'bg-green-900/40 border-green-700' },
  questionable: { label: 'Questionable', color: 'text-yellow-400', bg: 'bg-yellow-900/40 border-yellow-700' },
  unreliable: { label: 'Unreliable', color: 'text-red-400', bg: 'bg-red-900/40 border-red-700' },
  insufficient_data: { label: 'Insufficient Data', color: 'text-gray-400', bg: 'bg-gray-800/50 border-gray-600' },
};

const STANCE_ICONS = {
  supports: { icon: '✓', color: 'text-green-400', label: 'Supports' },
  contradicts: { icon: '✗', color: 'text-red-400', label: 'Contradicts' },
  neutral: { icon: '−', color: 'text-gray-500', label: 'Neutral' },
};

function ClaimCard({ claim, index }) {
  const [expanded, setExpanded] = useState(false);
  const config = VERDICT_CONFIG[claim.verdict] || VERDICT_CONFIG.unverified;

  return (
    <div className={`${config.bg} border ${config.border} rounded-xl p-4 transition-all duration-200`}>
      {/* Claim header */}
      <div className="flex items-start gap-3">
        <span className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${config.badge}`}>
          {config.icon}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${config.badge}`}>
              {config.label}
            </span>
            <span className="text-xs text-gray-500">
              Confidence: {Math.round(claim.confidence * 100)}%
            </span>
          </div>
          <p className={`text-sm ${config.text} leading-relaxed`}>
            "{claim.claim}"
          </p>
        </div>
      </div>

      {/* Corrected info */}
      {claim.corrected_info && (
        <div className="mt-3 ml-10 bg-blue-900/30 border border-blue-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-blue-400 text-xs font-semibold uppercase tracking-wide">
              ℹ Corrected Information
            </span>
          </div>
          <p className="text-sm text-blue-200 leading-relaxed">
            {claim.corrected_info}
          </p>
        </div>
      )}

      {/* Sources toggle */}
      {claim.sources && claim.sources.length > 0 && (
        <div className="mt-3 ml-10">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 transition-colors"
          >
            <svg
              className={`w-3 h-3 transform transition-transform ${expanded ? 'rotate-90' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            {expanded ? 'Hide' : 'Show'} {claim.sources.length} source{claim.sources.length !== 1 ? 's' : ''}
          </button>

          {expanded && (
            <div className="mt-2 space-y-2">
              {claim.sources.map((src, idx) => {
                const stance = STANCE_ICONS[src.stance] || STANCE_ICONS.neutral;
                return (
                  <a
                    key={idx}
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block bg-gray-900/50 hover:bg-gray-900/80 border border-gray-700 hover:border-gray-500 rounded-lg p-3 transition-all group"
                  >
                    <div className="flex items-start gap-2">
                      <span className={`text-sm ${stance.color} flex-shrink-0 mt-0.5`} title={stance.label}>
                        {stance.icon}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
                            {src.platform}
                          </span>
                          <span className="text-xs text-gray-600">{src.source}</span>
                        </div>
                        <p className="text-sm text-gray-300 group-hover:text-white line-clamp-1 font-medium">
                          {src.title}
                        </p>
                        {src.snippet && (
                          <p className="text-xs text-gray-500 line-clamp-2 mt-1 leading-relaxed">
                            {src.snippet}
                          </p>
                        )}
                      </div>
                      <svg className="h-3.5 w-3.5 text-gray-600 group-hover:text-gray-400 flex-shrink-0 mt-1 transition-colors"
                           fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </div>
                  </a>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CrossCheckResults({ crossCheck }) {
  if (!crossCheck || !crossCheck.claims || crossCheck.claims.length === 0) {
    return null;
  }

  const reliability = RELIABILITY_CONFIG[crossCheck.overall_reliability] || RELIABILITY_CONFIG.insufficient_data;

  const falseCount = crossCheck.claims.filter(c => c.verdict === 'likely_false').length;
  const disputedCount = crossCheck.claims.filter(c => c.verdict === 'disputed').length;
  const trueCount = crossCheck.claims.filter(c => c.verdict === 'likely_true').length;

  // Collect all unique source websites used across all claims
  const allSources = [];
  const seenSources = new Set();
  crossCheck.claims.forEach(claim => {
    (claim.sources || []).forEach(src => {
      const key = src.source || src.platform;
      if (key && !seenSources.has(key)) {
        seenSources.add(key);
        allSources.push({ name: key, url: src.url, platform: src.platform });
      }
    });
  });

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
          <span>🔍</span> Cross-Platform Verification
        </h3>
        <div className={`text-xs font-semibold px-3 py-1 rounded-full border ${reliability.bg}`}>
          <span className={reliability.color}>{reliability.label}</span>
        </div>
      </div>

      {/* Summary bar */}
      <div className="flex items-center gap-4 mb-4 text-xs">
        <span className="text-gray-500">
          {crossCheck.claims_checked} claim{crossCheck.claims_checked !== 1 ? 's' : ''} checked
        </span>
        <span className="text-gray-700">|</span>
        <span className="text-gray-500">
          {allSources.length} source{allSources.length !== 1 ? 's' : ''} consulted
        </span>
      </div>

      {/* Platforms & Sources Used */}
      <div className="mb-5 bg-gray-900/50 border border-gray-700 rounded-xl p-4">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>🌐</span> Websites &amp; Platforms Used for Verification
        </h4>
        {/* Platform badges */}
        <div className="flex flex-wrap gap-2 mb-3">
          {(crossCheck.platforms_searched || []).map((platform) => (
            <span
              key={platform}
              className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-blue-900/40 text-blue-300 border border-blue-800"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              {platform}
            </span>
          ))}
        </div>
        {/* Individual source websites */}
        {allSources.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {allSources.map((src) => (
              <a
                key={src.name}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full
                           bg-gray-800 text-gray-300 border border-gray-600
                           hover:bg-gray-700 hover:text-white hover:border-gray-500 transition-all"
              >
                <img
                  src={`https://www.google.com/s2/favicons?domain=${new URL(src.url).hostname}&sz=16`}
                  alt=""
                  className="w-3.5 h-3.5 rounded-sm"
                  onError={(e) => { e.target.style.display = 'none'; }}
                />
                {src.name}
                <svg className="w-2.5 h-2.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Verdict stats */}
      <div className="grid grid-cols-4 gap-2 mb-5">
        {[
          { label: 'True', count: trueCount, color: 'text-green-400', bg: 'bg-green-900/20' },
          { label: 'False', count: falseCount, color: 'text-red-400', bg: 'bg-red-900/20' },
          { label: 'Disputed', count: disputedCount, color: 'text-yellow-400', bg: 'bg-yellow-900/20' },
          { label: 'Unverified', count: crossCheck.claims.filter(c => c.verdict === 'unverified').length, color: 'text-gray-400', bg: 'bg-gray-800' },
        ].map((stat) => (
          <div key={stat.label} className={`${stat.bg} rounded-lg p-2 text-center`}>
            <div className={`text-lg font-bold ${stat.color}`}>{stat.count}</div>
            <div className="text-xs text-gray-500">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Alert if false claims found */}
      {(falseCount > 0 || disputedCount > 0) && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-red-400 text-sm">⚠</span>
            <p className="text-sm text-red-300">
              {falseCount > 0 && `${falseCount} claim${falseCount !== 1 ? 's' : ''} found to be likely false. `}
              {disputedCount > 0 && `${disputedCount} claim${disputedCount !== 1 ? 's' : ''} are disputed. `}
              See corrected information below.
            </p>
          </div>
        </div>
      )}

      {/* Claims list */}
      <div className="space-y-3">
        {crossCheck.claims.map((claim, idx) => (
          <ClaimCard key={idx} claim={claim} index={idx} />
        ))}
      </div>
    </div>
  );
}
