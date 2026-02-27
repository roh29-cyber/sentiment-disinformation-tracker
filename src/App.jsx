import React, { useState } from 'react';
import { analyzeInput } from './api/analyze.js';
import InputForm from './components/InputForm.jsx';
import RiskAlert from './components/RiskAlert.jsx';
import TrustScore from './components/TrustScore.jsx';
import SentimentChart from './components/SentimentChart.jsx';
import SimilarityScore from './components/SimilarityScore.jsx';
import ReasonsList from './components/ReasonsList.jsx';
import RelatedArticles from './components/RelatedArticles.jsx';
import FactChecks from './components/FactChecks.jsx';
import Entities from './components/Entities.jsx';
import CrossCheckResults from './components/CrossCheckResults.jsx';
import ScorePanel from './components/ScorePanel.jsx';
import EvidenceSummary from './components/EvidenceSummary.jsx';
import NewsCoverage from './components/NewsCoverage.jsx';
import GeminiAnalysis from './components/GeminiAnalysis.jsx';
import LoadingSpinner from './components/LoadingSpinner.jsx';
import ErrorAlert from './components/ErrorAlert.jsx';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async (input) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeInput(input);
      setResult(data);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'An unexpected error occurred. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <span className="text-2xl" aria-hidden="true">🛡️</span>
          <div>
            <h1 className="text-lg font-bold text-white leading-tight">
              Real-Time Narrative Risk Detection
            </h1>
            <p className="text-xs text-gray-500">
              Analyze URLs and topics for misinformation, sentiment, and coordination risks
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Input Section */}
        <section aria-label="Input section">
          <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6">
            <h2 className="text-base font-semibold text-gray-300 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 bg-brand rounded-full flex items-center justify-center text-xs font-bold">1</span>
              Enter a URL or Topic to Analyze
            </h2>
            <InputForm onAnalyze={handleAnalyze} loading={loading} />
          </div>
        </section>

        {/* Loading State */}
        {loading && (
          <section aria-label="Loading analysis">
            <div className="bg-gray-800/50 border border-gray-700 rounded-2xl">
              <LoadingSpinner />
            </div>
          </section>
        )}

        {/* Error State */}
        {error && !loading && (
          <section aria-label="Error message">
            <ErrorAlert error={error} onDismiss={() => setError(null)} />
          </section>
        )}

        {/* Results */}
        {result && !loading && (
          <section aria-label="Analysis results" className="space-y-6">
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-gray-300 flex items-center gap-2">
                <span className="w-6 h-6 bg-brand rounded-full flex items-center justify-center text-xs font-bold">2</span>
                Analysis Results
              </h2>
              <span className="text-xs text-gray-500 bg-gray-800 border border-gray-700 px-3 py-1 rounded-full">
                Input type: <span className="text-gray-300 capitalize">{result.input_type}</span>
              </span>
            </div>

            {/* Risk Alert — full width */}
            <RiskAlert riskLevel={result.risk_level} inputType={result.input_type}
                       misinformationScore={result.misinformation_score}
                       confidence={result.confidence} />

            {/* Evidence Summary */}
            {result.summary && (
              <EvidenceSummary summary={result.summary} sourcesChecked={result.sources_checked} />
            )}

            {/* News Coverage from NewsAPI */}
            {result.cross_check && (
              <NewsCoverage crossCheck={result.cross_check} />
            )}

            {/* Gemini AI Analysis */}
            {result.gemini_analysis && (
              <GeminiAnalysis geminiData={result.gemini_analysis} />
            )}

            {/* Score Gauges + Cross-Check */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ScorePanel
                misinformationScore={result.misinformation_score}
                reputationScore={result.reputation_risk_score}
                reputationLevel={result.reputation_risk_level}
                confidence={result.confidence}
              />
              <TrustScore score={result.source_trust_score} />
            </div>

            {/* Cross-Platform Verification — full width */}
            {result.cross_check && (
              <CrossCheckResults crossCheck={result.cross_check} />
            )}

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <SimilarityScore score={result.similarity_score} />
            </div>

            {/* Sentiment + Reasons */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <SentimentChart sentiment={result.sentiment} />
              <ReasonsList reasons={result.reasons} riskLevel={result.risk_level} />
            </div>

            {/* Entities */}
            {result.related?.entities?.length > 0 && (
              <Entities entities={result.related.entities} />
            )}

            {/* Related Articles + Fact Checks */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <RelatedArticles articles={result.related?.articles} />
              <FactChecks factChecks={result.related?.fact_checks} />
            </div>
          </section>
        )}

        {/* Empty state */}
        {!loading && !result && !error && (
          <section aria-label="Getting started" className="text-center py-16">
            <div className="text-6xl mb-4" aria-hidden="true">🔎</div>
            <h2 className="text-xl font-semibold text-gray-400 mb-2">Ready to Analyze</h2>
            <p className="text-gray-600 max-w-md mx-auto text-sm">
              Enter a website URL or a topic/keyword above to detect narrative risks,
              analyze sentiment, and check source credibility.
            </p>
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto text-left">
              {[
                { icon: '🌐', title: 'URL Analysis', desc: 'Scrape and analyze any webpage for risk signals' },
                { icon: '📝', title: 'Topic Search', desc: 'Search the web for content about any topic or keyword' },
                { icon: '📊', title: 'Full Report', desc: 'Get sentiment, trust scores, entities, and fact-checks' },
              ].map((feature) => (
                <div key={feature.title}
                     className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                  <div className="text-2xl mb-2" aria-hidden="true">{feature.icon}</div>
                  <h3 className="text-sm font-semibold text-gray-300 mb-1">{feature.title}</h3>
                  <p className="text-xs text-gray-500">{feature.desc}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer className="border-t border-gray-800 mt-16 py-6 text-center text-xs text-gray-600">
        Real-Time Narrative Risk Detection System — Powered by VADER, TF-IDF, spaCy &amp; Recharts
      </footer>
    </div>
  );
}
