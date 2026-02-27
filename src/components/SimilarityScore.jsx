import React from 'react';

function getSimilarityConfig(score) {
  if (score > 0.6) return { color: 'text-red-400', bar: 'bg-red-500', label: 'High Coordination' };
  if (score > 0.4) return { color: 'text-yellow-400', bar: 'bg-yellow-500', label: 'Moderate Coordination' };
  return { color: 'text-emerald-400', bar: 'bg-emerald-500', label: 'Low Coordination' };
}

export default function SimilarityScore({ score }) {
  const pct = Math.round(score * 100);
  const { color, bar, label } = getSimilarityConfig(score);

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Coordination / Similarity Score
      </h3>
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="flex justify-between mb-2">
            <span className={`text-sm font-medium ${color}`}>{label}</span>
            <span className={`text-sm font-bold ${color}`}>{score.toFixed(4)}</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3" role="progressbar"
               aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div
              className={`${bar} h-3 rounded-full transition-all duration-700`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Measures how similar text chunks are to each other — high scores may indicate coordinated messaging.
          </p>
        </div>
        <div className={`text-3xl font-bold ${color} min-w-[4rem] text-right`}>
          {pct}%
        </div>
      </div>
    </div>
  );
}
