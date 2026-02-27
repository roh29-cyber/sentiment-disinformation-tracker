import React from 'react';

function getTrustColor(score) {
  if (score >= 0.7) return { bar: 'bg-emerald-500', text: 'text-emerald-400', label: 'High Trust' };
  if (score >= 0.4) return { bar: 'bg-yellow-500', text: 'text-yellow-400', label: 'Moderate Trust' };
  return { bar: 'bg-red-500', text: 'text-red-400', label: 'Low Trust' };
}

export default function TrustScore({ score }) {
  const pct = Math.round(score * 100);
  const { bar, text, label } = getTrustColor(score);

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Source Trust Score
      </h3>
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="flex justify-between mb-2">
            <span className={`text-sm font-medium ${text}`}>{label}</span>
            <span className={`text-sm font-bold ${text}`}>{score.toFixed(2)}</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3" role="progressbar"
               aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div
              className={`${bar} h-3 rounded-full transition-all duration-700`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-xs text-gray-600">0.0</span>
            <span className="text-xs text-gray-600">1.0</span>
          </div>
        </div>
        <div className={`text-3xl font-bold ${text} min-w-[4rem] text-right`}>
          {pct}%
        </div>
      </div>
    </div>
  );
}
