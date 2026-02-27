import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const COLORS = {
  positive: '#10b981',
  neutral: '#6b7280',
  negative: '#ef4444',
};

const RADIAN = Math.PI / 180;

function CustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent < 0.05) return null;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central"
          fontSize={13} fontWeight="bold">
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

export default function SentimentChart({ sentiment }) {
  const data = [
    { name: 'Positive', value: sentiment.positive, color: COLORS.positive },
    { name: 'Neutral', value: sentiment.neutral, color: COLORS.neutral },
    { name: 'Negative', value: sentiment.negative, color: COLORS.negative },
  ].filter((d) => d.value > 0);

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Sentiment Analysis
      </h3>

      <div className="flex flex-wrap gap-3 mb-4">
        {[
          { label: 'Positive', value: sentiment.positive, color: 'text-emerald-400', bg: 'bg-emerald-900/40 border-emerald-700' },
          { label: 'Neutral', value: sentiment.neutral, color: 'text-gray-400', bg: 'bg-gray-700/40 border-gray-600' },
          { label: 'Negative', value: sentiment.negative, color: 'text-red-400', bg: 'bg-red-900/40 border-red-700' },
        ].map((item) => (
          <div key={item.label} className={`flex-1 min-w-[80px] rounded-xl border p-3 text-center ${item.bg}`}>
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}%</div>
            <div className="text-xs text-gray-500 mt-1">{item.label}</div>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={85}
            dataKey="value"
            labelLine={false}
            label={CustomLabel}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
            labelStyle={{ color: '#f9fafb' }}
            formatter={(value) => [`${value}%`, '']}
          />
          <Legend
            formatter={(value) => <span style={{ color: '#9ca3af', fontSize: 12 }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
