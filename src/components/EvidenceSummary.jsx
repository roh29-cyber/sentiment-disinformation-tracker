import React from 'react';

export default function EvidenceSummary({ summary, sourcesChecked }) {
  return (
    <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Evidence Summary
      </h3>
      <p className="text-gray-300 text-sm leading-relaxed">{summary}</p>

      {sourcesChecked && sourcesChecked.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-700">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Sources Checked ({sourcesChecked.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {sourcesChecked.map((url, idx) => {
              let domain;
              try {
                domain = new URL(url).hostname.replace('www.', '');
              } catch {
                domain = url;
              }
              return (
                <a key={idx} href={url} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1.5 bg-gray-700/60 hover:bg-gray-700 text-gray-400 hover:text-gray-200 text-xs px-2.5 py-1 rounded-full border border-gray-600 transition-colors">
                  <img src={`https://www.google.com/s2/favicons?domain=${domain}&sz=16`}
                       alt="" className="w-3.5 h-3.5 rounded-sm" />
                  {domain}
                </a>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
