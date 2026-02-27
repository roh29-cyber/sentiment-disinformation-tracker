import React from 'react';

export default function ReasonsList({ reasons, riskLevel }) {
  const iconMap = {
    HIGH: '🚨',
    MEDIUM: '⚠️',
    LOW: '✅',
  };

  const colorMap = {
    HIGH: 'border-red-700 bg-red-900/20 text-red-300',
    MEDIUM: 'border-yellow-700 bg-yellow-900/20 text-yellow-300',
    LOW: 'border-emerald-700 bg-emerald-900/20 text-emerald-300',
  };

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Risk Reasons
      </h3>
      {reasons.length === 0 ? (
        <p className="text-gray-500 text-sm">No specific risk reasons identified.</p>
      ) : (
        <ul className="space-y-2" role="list">
          {reasons.map((reason, idx) => (
            <li
              key={idx}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${colorMap[riskLevel]}`}
            >
              <span className="mt-0.5 flex-shrink-0" aria-hidden="true">{iconMap[riskLevel]}</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
