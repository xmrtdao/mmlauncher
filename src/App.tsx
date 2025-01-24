import React, { useState } from 'react';
import { ChevronRight, ChevronLeft, Languages, Terminal, Download, Send, Wallet, Copy } from 'lucide-react';
import { translations } from './translations';

function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [language, setLanguage] = useState<'en' | 'es'>('en');
  const t = translations[language];

  const nextStep = () => setCurrentStep(prev => Math.min(prev + 1, 3));
  const prevStep = () => setCurrentStep(prev => Math.max(prev - 1, 1));

  return (
    <div className="min-h-screen bg-gradient-to-b from-violet-900 to-purple-800 text-white">
      {/* Branding Header */}
      <div className="fixed top-0 left-0 right-0 bg-black/20 backdrop-blur-sm py-4 px-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="w-8 h-8 text-orange-500" />
          <span className="font-bold text-xl">MobileMonero</span>
        </div>
        <button
          onClick={() => setLanguage(lang => lang === 'en' ? 'es' : 'en')}
          className="flex items-center gap-2 bg-white/10 rounded-full px-4 py-2 hover:bg-white/20 transition-all"
        >
          <Languages size={20} />
          <span>{language.toUpperCase()}</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 pt-24 pb-16">
        {/* Progress Bar */}
        <div className="flex justify-between mb-8 px-4">
          {[1, 2, 3].map(step => (
            <div
              key={step}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500 ${
                step === currentStep
                  ? 'bg-orange-500 scale-110'
                  : step < currentStep
                  ? 'bg-green-500'
                  : 'bg-white/20'
              }`}
            >
              {step}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="relative h-[calc(100vh-280px)] flex items-center justify-center">
          <div className="w-full max-w-md mx-auto bg-white/10 backdrop-blur-lg rounded-xl p-6 shadow-xl animate-fadeIn border border-white/10">
            {currentStep === 1 && (
              <div className="space-y-4">
                <Download className="w-12 h-12 mx-auto mb-4 text-orange-300" />
                <h2 className="text-2xl font-bold text-center mb-4">{t.step1Title}</h2>
                <p className="text-center mb-6">{t.step1Description}</p>
                <div className="flex justify-center gap-4">
                  <a
                    href="https://apps.apple.com/us/app/termux/id1234567890"
                    className="bg-orange-500/20 hover:bg-orange-500/30 px-6 py-3 rounded-lg transition-all flex items-center gap-2"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    App Store
                  </a>
                  <a
                    href="https://play.google.com/store/apps/details?id=com.termux"
                    className="bg-orange-500/20 hover:bg-orange-500/30 px-6 py-3 rounded-lg transition-all flex items-center gap-2"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Play Store
                  </a>
                </div>
              </div>
            )}

            {currentStep === 2 && (
              <div className="space-y-4">
                <Terminal className="w-12 h-12 mx-auto mb-4 text-orange-300" />
                <h2 className="text-2xl font-bold text-center mb-4">{t.step2Title}</h2>
                <p className="text-sm text-center mb-6">{t.step2Description}</p>
                <div className="bg-black/30 p-4 rounded-lg font-mono text-sm">
                  <code>pkg install python</code>
                  <button
                    onClick={() => navigator.clipboard.writeText('pkg install python')}
                    className="ml-2 text-orange-300 hover:text-orange-200"
                  >
                    <Copy size={16} />
                  </button>
                </div>
              </div>
            )}

            {currentStep === 3 && (
              <div className="space-y-4">
                <Send className="w-12 h-12 mx-auto mb-4 text-orange-300" />
                <h2 className="text-2xl font-bold text-center mb-4">{t.step3Title}</h2>
                <p className="text-center mb-6">{t.step3Description}</p>
                <div className="bg-black/30 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                  <code>curl -s https://gist.githubusercontent.com/DevGruGold/1935cefeb0920d88c3fad17705d14431/raw &gt; script.py && python3 script.py</code>
                  <button
                    onClick={() => navigator.clipboard.writeText('curl -s https://gist.githubusercontent.com/DevGruGold/1935cefeb0920d88c3fad17705d14431/raw > script.py && python3 script.py')}
                    className="ml-2 text-orange-300 hover:text-orange-200"
                  >
                    <Copy size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Buttons */}
        <div className="fixed bottom-20 left-0 right-0 flex justify-between px-8">
          {currentStep > 1 && (
            <button
              onClick={prevStep}
              className="flex items-center gap-2 bg-white/10 rounded-full px-6 py-3 hover:bg-white/20 transition-all"
            >
              <ChevronLeft size={20} />
              {t.previous}
            </button>
          )}
          {currentStep < 3 && (
            <button
              onClick={nextStep}
              className="flex items-center gap-2 bg-orange-500 rounded-full px-6 py-3 hover:bg-orange-600 transition-all ml-auto"
            >
              {t.next}
              <ChevronRight size={20} />
            </button>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-black/20 backdrop-blur-sm py-2 text-center text-sm">
        <a href="mailto:info@mobilemonero.com" className="hover:text-orange-300 transition-all">
          {t.support}
        </a>
      </footer>
    </div>
  );
}

export default App;