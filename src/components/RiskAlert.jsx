import React from 'react';

const RISK_CONFIG = {
  LOW: {
    bg: 'bg-emerald-900/40',
    border: 'border-emerald-500',
    text: 'text-emerald-400',
    badge: 'bg-emerald-500',
    icon: '✅',
    label: 'LOW RISK',
  },
  MEDIUM: {
    bg: 'bg-yellow-900/40',
    border: 'border-yellow-500',
    text: 'text-yellow-400',
    badge: 'bg-yellow-500',
    icon: '⚠️',
    label: 'MEDIUM RISK',
  },
  HIGH: {
    bg: 'bg-red-900/40',
    border: 'border-red-500',
    text: 'text-red-400',
    badge: 'bg-red-500',
    icon: '🚨',
    label: 'HIGH RISK',
  },
};

export default function RiskAlert({ riskLevel, inputType, misinformationScore, confidence }) {
  const config = RISK_CONFIG[riskLevel] || RISK_CONFIG.LOW;

  return (
    <div
      role="alert"
      aria-label={`Risk level: ${riskLevel}`}
      className={`rounded-2xl border-2 ${config.bg} ${config.border} p-6 flex items-center gap-4`}
    >
      <span className="text-4xl" aria-hidden="true">{config.icon}</span>
      <div className="flex-1">
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`text-2xl font-bold ${config.text}`}>{config.label}</span>
          <span className={`${config.badge} text-white text-xs font-bold px-3 py-1 rounded-full uppercase`}>
            {riskLevel}
          </span>
          {misinformationScore !== undefined && (
            <span className={`${config.border} border text-xs font-bold px-3 py-1 rounded-full ${config.text}`}>
              Score: {misinformationScore}/100
            </span>
          )}
          {confidence && (
            <span className="text-gray-400 text-xs bg-gray-700/60 px-2.5 py-1 rounded-full">
              Confidence: {confidence}
            </span>
          )}
          <span className="text-gray-400 text-sm">
            Input type: <span className="text-gray-200 font-medium capitalize">{inputType}</span>
          </span>
        </div>
        <p className="text-gray-400 text-sm mt-1">
          {riskLevel === 'HIGH' && 'This content shows significant risk indicators. Exercise caution.'}
          {riskLevel === 'MEDIUM' && 'This content shows moderate risk indicators. Verify with trusted sources.'}
          {riskLevel === 'LOW' && 'This content appears to be from credible sources with balanced sentiment.'}
        </p>
      </div>
    </div>
  );
}
