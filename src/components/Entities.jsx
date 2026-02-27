import React from 'react';

const TYPE_CONFIG = {
  PERSON: { color: 'bg-blue-900/50 text-blue-300 border-blue-700', icon: '👤' },
  ORG: { color: 'bg-orange-900/50 text-orange-300 border-orange-700', icon: '🏢' },
  LOCATION: { color: 'bg-teal-900/50 text-teal-300 border-teal-700', icon: '📍' },
};

export default function Entities({ entities }) {
  const grouped = {
    PERSON: entities.filter((e) => e.type === 'PERSON'),
    ORG: entities.filter((e) => e.type === 'ORG'),
    LOCATION: entities.filter((e) => e.type === 'LOCATION'),
  };

  const hasEntities = entities && entities.length > 0;

  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
        <span>🏷️</span> Key Entities
      </h3>

      {!hasEntities ? (
        <p className="text-gray-500 text-sm">No named entities detected.</p>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([type, items]) => {
            if (items.length === 0) return null;
            const config = TYPE_CONFIG[type] || TYPE_CONFIG.ORG;
            return (
              <div key={type}>
                <div className="flex items-center gap-2 mb-2">
                  <span aria-hidden="true">{config.icon}</span>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{type}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {items.map((entity, idx) => (
                    <span
                      key={idx}
                      className={`inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5
                                  rounded-full border ${config.color}`}
                    >
                      {entity.name}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
