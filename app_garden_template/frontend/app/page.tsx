'use client';

import { useState, useEffect } from 'react';
import { fetchModels, summarizeTranscript, Model } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function Home() {
  // Redirect to RFP Discovery page
  useEffect(() => {
    window.location.href = '/rfp';
  }, []);

  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [transcript, setTranscript] = useState<string>('');
  const [summary, setSummary] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const modelList = await fetchModels();
      setModels(modelList);
      if (modelList.length > 0) {
        setSelectedModel(modelList[0].name);
      }
    } catch (err) {
      setError('Failed to load models. Please try again.');
      console.error('Error loading models:', err);
    }
  };

  const handleSummarize = async () => {
    if (!transcript.trim()) {
      setError('Please enter a transcript to summarize.');
      return;
    }

    if (!selectedModel) {
      setError('Please select a model.');
      return;
    }

    setIsLoading(true);
    setError('');
    setSummary('');

    try {
      const result = await summarizeTranscript({
        transcript: transcript,
        model_name: selectedModel,
      });
      setSummary(result.summary);
    } catch (err) {
      setError('Failed to summarize transcript. Please try again.');
      console.error('Error summarizing:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen py-12 px-4 sm:px-6 lg:px-8 page-transition">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12 p-8 rounded-2xl bg-gradient-to-br from-primary/10 to-transparent border border-white/10 slide-up">
          <img 
            src="/kamiwaza-logo-with-text.png" 
            alt="Kamiwaza Logo" 
            style={{ height: '50px' }} 
            className="mx-auto mb-6"
          />
          <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">
            Meeting Transcript Summarizer
          </h1>
          <p className="text-lg text-muted-foreground">
            Powered by Kamiwaza AI Models
          </p>
        </div>

        <div className="bg-card rounded-xl p-6 mb-8 shadow-lg border border-white/10 card-hover fade-in">
          <div className="mb-6">
            <label htmlFor="model" className="block text-sm font-medium text-white mb-2">
              Select AI Model
            </label>
            <select
              id="model"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-4 py-3 bg-input border border-border rounded-lg text-white transition-all duration-300 hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/25"
            >
              {models.map((model) => (
                <option key={model.id} value={model.name} className="bg-surface-elevated">
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          <div className="mb-6">
            <label htmlFor="transcript" className="block text-sm font-medium text-white mb-2">
              Meeting Transcript
            </label>
            <textarea
              id="transcript"
              rows={10}
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Paste your meeting transcript here..."
              className="w-full px-4 py-3 bg-input border border-border rounded-lg text-white placeholder-muted-foreground transition-all duration-300 hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/25 resize-none"
            />
          </div>

          {error && (
            <div className="mb-4 p-4 bg-destructive/15 border border-destructive/30 text-destructive rounded-lg">
              {error}
            </div>
          )}

          <button
            onClick={handleSummarize}
            disabled={isLoading || !selectedModel || !transcript.trim()}
            className="w-full py-3 px-6 bg-primary text-primary-foreground font-medium rounded-lg transition-all duration-300 hover:bg-primary-dark hover:shadow-lg hover:transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none"
          >
            {isLoading ? 'Summarizing...' : 'Summarize Transcript'}
          </button>
        </div>

        {isLoading && (
          <div className="bg-primary/10 border border-primary/30 rounded-xl p-6 shadow-lg slide-up">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}>
              <div className="spinner"></div>
              <span className="text-primary font-medium">Summarizing your transcript...</span>
            </div>
          </div>
        )}

        {summary && !isLoading && (
          <div className="bg-card rounded-xl p-6 shadow-lg border border-white/10 card-hover slide-up">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
              <span className="w-1 h-6 bg-primary rounded-full mr-3"></span>
              Summary
            </h2>
            <div className="prose prose-invert max-w-none text-muted-foreground overflow-y-auto max-h-[600px] pr-2">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({children}) => <h1 className="text-2xl font-bold mb-4 text-white">{children}</h1>,
                  h2: ({children}) => <h2 className="text-xl font-semibold mb-3 text-white">{children}</h2>,
                  h3: ({children}) => <h3 className="text-lg font-medium mb-2 text-white">{children}</h3>,
                  p: ({children}) => <p className="mb-4 leading-relaxed">{children}</p>,
                  ul: ({children}) => <ul className="mb-4 ml-6 list-disc">{children}</ul>,
                  ol: ({children}) => <ol className="mb-4 ml-6 list-decimal">{children}</ol>,
                  li: ({children}) => <li className="mb-1">{children}</li>,
                  strong: ({children}) => <strong className="font-semibold text-white">{children}</strong>,
                  em: ({children}) => <em className="italic">{children}</em>,
                  blockquote: ({children}) => (
                    <blockquote className="border-l-4 border-primary/50 pl-4 my-4 italic">
                      {children}
                    </blockquote>
                  ),
                  code: ({children}) => {
                    const inline = !String(children).includes('\n');
                    return inline ? (
                      <code className="bg-surface-elevated px-1 py-0.5 rounded text-sm font-mono">{children}</code>
                    ) : (
                      <code className="block bg-surface-elevated p-4 rounded-lg overflow-x-auto font-mono text-sm">{children}</code>
                    );
                  },
                  table: ({children}) => (
                    <div className="overflow-x-auto mb-4">
                      <table className="min-w-full divide-y divide-border">{children}</table>
                    </div>
                  ),
                  thead: ({children}) => <thead className="bg-surface-elevated">{children}</thead>,
                  tbody: ({children}) => <tbody className="divide-y divide-border">{children}</tbody>,
                  tr: ({children}) => <tr>{children}</tr>,
                  th: ({children}) => <th className="px-4 py-2 text-left font-semibold text-white">{children}</th>,
                  td: ({children}) => <td className="px-4 py-2">{children}</td>,
                }}
              >
                {summary}
              </ReactMarkdown>
            </div>
            <div className="mt-6 pt-4 border-t border-divider">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary/15 text-primary">
                Generated with: {selectedModel}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}