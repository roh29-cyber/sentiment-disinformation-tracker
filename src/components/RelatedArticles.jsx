import React from 'react';

function ArticleCard({ title, url, source }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Read article: ${title}`}
      className="block bg-gray-700/50 hover:bg-gray-700 border border-gray-600 hover:border-brand
                 rounded-xl p-4 transition-all duration-200 group"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-200 group-hover:text-white line-clamp-2 leading-snug">
            {title || 'Untitled Article'}
          </p>
          {source && (
            <span className="inline-block mt-2 text-xs text-brand bg-brand/10 px-2 py-0.5 rounded-full">
              {source}
            </span>
          )}
        </div>
        <svg className="h-4 w-4 text-gray-500 group-hover:text-brand flex-shrink-0 mt-0.5 transition-colors"
             fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </div>
    </a>
  );
}

export default function RelatedArticles({ articles }) {
  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
        <span>📰</span> Related Articles
      </h3>
      {!articles || articles.length === 0 ? (
        <p className="text-gray-500 text-sm">No related articles found.</p>
      ) : (
        <div className="space-y-3">
          {articles.map((article, idx) => (
            <ArticleCard key={idx} {...article} />
          ))}
        </div>
      )}
    </div>
  );
}
