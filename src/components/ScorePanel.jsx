import React from 'react';

function getScoreColor(score) {
  if (score >= 70) return { ring: 'text-red-500', bg: 'bg-red-500', trail: 'text-red-900' };
  if (score >= 35) return { ring: 'text-yellow-500', bg: 'bg-yellow-500', trail: 'text-yellow-900' };
  return { ring: 'text-emerald-500', bg: 'bg-emerald-500', trail: 'text-emerald-900' };
}

function ScoreGauge({ score, label, subtitle }) {
  const { ring, trail } = getScoreColor(score);
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-28 h-28">
        <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="8"
                  className={trail} style={{ opacity: 0.2 }} />
          <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="8"
                  className={ring}
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={offset}
                  style={{ transition: 'stroke-dashoffset 1s ease-out' }} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl font-bold ${ring}`}>{score}</span>
        </div>
      </div>
      <p className="text-sm font-semibold text-gray-300 mt-2">{label}</p>
      {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
    </div>
  );
}

export default function ScorePanel({ misinformationScore, reputationScore, reputationLevel, confidence }) {
  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Risk Scores
      </h3>
      <div className="flex items-center justify-around gap-4 flex-wrap">
        <ScoreGauge
          score={misinformationScore}
          label="Misinfo Risk"
          subtitle={`Confidence: ${confidence}`}
        />
        <ScoreGauge
          score={reputationScore}
          label="Reputation Risk"
          subtitle={reputationLevel}
        />
      </div>
    </div>
  );
}
