import React from 'react';

const STEPS = [
  { icon: '🔍', label: 'Detecting input type…' },
  { icon: '🌐', label: 'Fetching content…' },
  { icon: '🛡️', label: 'Checking source credibility…' },
  { icon: '💬', label: 'Analyzing sentiment…' },
  { icon: '🔗', label: 'Detecting coordination patterns…' },
  { icon: '⚡', label: 'Computing risk score…' },
  { icon: '📰', label: 'Fetching related articles…' },
];

export default function LoadingSpinner() {
  const [step, setStep] = React.useState(0);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setStep((prev) => (prev + 1) % STEPS.length);
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-6" role="status" aria-live="polite">
      <div className="relative">
        <div className="w-20 h-20 rounded-full border-4 border-gray-700 border-t-brand animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center text-3xl">
          {STEPS[step].icon}
        </div>
      </div>
      <div className="text-center">
        <p className="text-gray-300 font-medium text-lg">Analyzing content…</p>
        <p className="text-gray-500 text-sm mt-1 transition-all duration-300">
          {STEPS[step].label}
        </p>
      </div>
      <div className="flex gap-1.5">
        {STEPS.map((_, idx) => (
          <div
            key={idx}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              idx === step ? 'w-6 bg-brand' : 'w-1.5 bg-gray-700'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
