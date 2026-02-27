import React from 'react';

const TRUST_COLORS = {
  'Official/Govt': { bg: 'bg-purple-900/30', border: 'border-purple-700', text: 'text-purple-300', dot: 'bg-purple-400' },
  'Trusted Media': { bg: 'bg-blue-900/30', border: 'border-blue-700', text: 'text-blue-300', dot: 'bg-blue-400' },
  'News':          { bg: 'bg-gray-800/60', border: 'border-gray-600', text: 'text-gray-300', dot: 'bg-gray-400' },
};

function getDomain(url) {
  try { return new URL(url).hostname.replace('www.', ''); } catch { return ''; }
}

function NewsCard({ article }) {
  const domain = getDomain(article.url);
  // Extract trust label from platform e.g. "NewsAPI (Trusted Media)" -> "Trusted Media"
  const trustMatch = (article.platform || '').match(/\(([^)]+)\)/);
  const trustLabel = trustMatch ? trustMatch[1] : 'News';
  const colors = TRUST_COLORS[trustLabel] || TRUST_COLORS['News'];

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className={`block ${colors.bg} border ${colors.border} rounded-xl p-4 hover:brightness-125 transition-all group`}
    >
      <div className="flex items-start gap-3">
        {/* Favicon */}
        <img
          src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
          alt=""
          className="w-6 h-6 rounded mt-0.5 flex-shrink-0"
          onError={(e) => { e.target.style.display = 'none'; }}
        />
        <div className="flex-1 min-w-0">
          {/* Source + Trust badge */}
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-xs font-semibold text-gray-200">
              {article.source || domain}
            </span>
            <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${colors.bg} ${colors.text} border ${colors.border}`}>
              <span className={`w-1 h-1 rounded-full ${colors.dot}`} />
              {trustLabel}
            </span>
          </div>
          {/* Title */}
          <h4 className="text-sm font-medium text-gray-100 group-hover:text-white leading-snug line-clamp-2">
            {article.title}
          </h4>
          {/* Snippet */}
          {article.snippet && (
            <p className="text-xs text-gray-400 mt-1.5 line-clamp-2 leading-relaxed">
              {article.snippet}
            </p>
          )}
        </div>
        {/* External link icon */}
        <svg className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-300 flex-shrink-0 mt-1 transition-colors"
             fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </div>
    </a>
  );
}

export default function NewsCoverage({ crossCheck }) {
  if (!crossCheck?.claims) return null;

  // Collect all NewsAPI sources from all claims
  const newsArticles = [];
  const seen = new Set();

  crossCheck.claims.forEach(claim => {
    (claim.sources || []).forEach(src => {
      if (src.platform && src.platform.startsWith('NewsAPI') && src.url && !seen.has(src.url)) {
        seen.add(src.url);
        newsArticles.push(src);
      }
    });
  });

  if (newsArticles.length === 0) return null;

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
          <span>📰</span> News Coverage
        </h3>
        <span className="text-xs text-gray-500 bg-gray-900 px-2.5 py-1 rounded-full border border-gray-700">
          {newsArticles.length} article{newsArticles.length !== 1 ? 's' : ''} found
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {newsArticles.map((article, idx) => (
          <NewsCard key={idx} article={article} />
        ))}
      </div>
    </div>
  );
}
