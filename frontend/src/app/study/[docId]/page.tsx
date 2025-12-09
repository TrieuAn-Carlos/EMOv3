'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'next/navigation';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import {
  ChevronLeft,
  ChevronRight,
  Brain,
  FileText,
  Loader2,
  CheckCircle,
  XCircle,
  RotateCcw
} from 'lucide-react';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const API_BASE = 'http://localhost:8000/api';

interface Question {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

interface Quiz {
  quiz_id: string;
  title: string;
  difficulty: string;
  questions: Question[];
  doc_id: string;
  page_number: number | null;
  source: string;
}

interface DocumentInfo {
  id: string;
  filename: string;
  page_count: number;
  uploaded_at: string;
}

export default function StudyPage() {
  const params = useParams();
  const docId = params.docId as string;

  // Document state
  const [documentInfo, setDocumentInfo] = useState<DocumentInfo | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quiz state
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [quizLoading, setQuizLoading] = useState(false);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});
  const [showResults, setShowResults] = useState(false);
  const [difficulty, setDifficulty] = useState<string>('Beginner');

  // Selection state
  const [selectedText, setSelectedText] = useState<string>('');
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  // Fetch document info
  useEffect(() => {
    async function fetchDocument() {
      try {
        const res = await fetch(`${API_BASE}/documents/${docId}`);
        if (!res.ok) throw new Error('Document not found');
        const data = await res.json();
        setDocumentInfo(data);
        setNumPages(data.page_count);
        // For actual PDF viewing, you'd need to serve the PDF file
        // This is a placeholder - in production, add a /documents/{id}/file endpoint
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load document');
        setLoading(false);
      }
    }
    if (docId) fetchDocument();
  }, [docId]);

  // Handle text selection for "Quiz Me" feature
  const handleTextSelection = useCallback(() => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim().length > 20) {
      const text = selection.toString().trim();
      setSelectedText(text);

      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left + rect.width / 2,
        y: rect.top - 10
      });
      setShowTooltip(true);
    } else {
      setShowTooltip(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener('mouseup', handleTextSelection);
    return () => document.removeEventListener('mouseup', handleTextSelection);
  }, [handleTextSelection]);

  // Generate quiz for current page
  const generatePageQuiz = async () => {
    setQuizLoading(true);
    setQuiz(null);
    setSelectedAnswers({});
    setShowResults(false);

    try {
      const res = await fetch(`${API_BASE}/documents/quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: docId,
          page: currentPage,
          difficulty,
          num_questions: 5
        })
      });

      if (!res.ok) throw new Error('Failed to generate quiz');
      const data = await res.json();
      setQuiz(data);
    } catch (err) {
      console.error('Quiz generation error:', err);
    } finally {
      setQuizLoading(false);
    }
  };

  // Generate quiz from highlighted text
  const generateHighlightQuiz = async () => {
    if (!selectedText) return;

    setShowTooltip(false);
    setQuizLoading(true);
    setQuiz(null);
    setSelectedAnswers({});
    setShowResults(false);

    try {
      const res = await fetch(`${API_BASE}/documents/quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: docId,
          context: selectedText,
          difficulty,
          num_questions: 3
        })
      });

      if (!res.ok) throw new Error('Failed to generate quiz');
      const data = await res.json();
      setQuiz(data);
    } catch (err) {
      console.error('Quiz generation error:', err);
    } finally {
      setQuizLoading(false);
      setSelectedText('');
    }
  };

  // Select answer
  const selectAnswer = (questionIndex: number, answer: string) => {
    if (showResults) return;
    setSelectedAnswers(prev => ({ ...prev, [questionIndex]: answer }));
  };

  // Check answers
  const checkAnswers = () => {
    setShowResults(true);
  };

  // Reset quiz
  const resetQuiz = () => {
    setSelectedAnswers({});
    setShowResults(false);
  };

  // Calculate score
  const getScore = () => {
    if (!quiz) return { correct: 0, total: 0 };
    let correct = 0;
    quiz.questions.forEach((q, i) => {
      if (selectedAnswers[i] === q.correct_answer) correct++;
    });
    return { correct, total: quiz.questions.length };
  };

  if (loading) {
    return (
      <div className="study-loading">
        <Loader2 className="animate-spin" size={48} />
        <p>Loading document...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="study-error">
        <FileText size={48} />
        <h2>Document Not Found</h2>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="study-container">
      {/* Tooltip for text selection */}
      {showTooltip && (
        <div
          className="quiz-tooltip"
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y
          }}
        >
          <button onClick={generateHighlightQuiz}>
            <Brain size={16} />
            Quiz Me
          </button>
        </div>
      )}

      <PanelGroup direction="horizontal" className="study-panels">
        {/* PDF Panel */}
        <Panel defaultSize={50} minSize={30} className="pdf-panel">
          <div className="pdf-header">
            <h2>{documentInfo?.filename}</h2>
            <div className="page-nav">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
              >
                <ChevronLeft size={20} />
              </button>
              <span>Page {currentPage} of {numPages}</span>
              <button
                onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))}
                disabled={currentPage >= numPages}
              >
                <ChevronRight size={20} />
              </button>
            </div>
          </div>

          <div className="pdf-viewer">
            {/* PDF content would render here */}
            {/* For now, showing page content from backend */}
            <PageContent docId={docId} pageNumber={currentPage} />
          </div>
        </Panel>

        {/* Resize Handle */}
        <PanelResizeHandle className="resize-handle" />

        {/* Quiz Panel */}
        <Panel defaultSize={50} minSize={30} className="quiz-panel">
          <div className="quiz-header">
            <h2><Brain size={24} /> SocratiQ</h2>
            <div className="quiz-controls">
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
              >
                <option value="Beginner">Beginner</option>
                <option value="Intermediate">Intermediate</option>
                <option value="Advanced">Advanced</option>
              </select>
              <button
                onClick={generatePageQuiz}
                disabled={quizLoading}
                className="generate-btn"
              >
                {quizLoading ? <Loader2 className="animate-spin" size={16} /> : <Brain size={16} />}
                Quiz Page {currentPage}
              </button>
            </div>
          </div>

          <div className="quiz-content">
            {quizLoading && (
              <div className="quiz-loading">
                <Loader2 className="animate-spin" size={32} />
                <p>Generating quiz...</p>
              </div>
            )}

            {!quiz && !quizLoading && (
              <div className="quiz-empty">
                <Brain size={48} />
                <h3>Ready to Learn?</h3>
                <p>Click "Quiz Page X" to generate a quiz for the current page, or highlight text and click "Quiz Me".</p>
              </div>
            )}

            {quiz && !quizLoading && (
              <div className="quiz-container">
                <div className="quiz-title">
                  <h3>{quiz.title}</h3>
                  <span className={`difficulty-badge ${quiz.difficulty.toLowerCase()}`}>
                    {quiz.difficulty}
                  </span>
                </div>

                {showResults && (
                  <div className="score-banner">
                    Score: {getScore().correct} / {getScore().total}
                    <button onClick={resetQuiz} className="retry-btn">
                      <RotateCcw size={16} /> Try Again
                    </button>
                  </div>
                )}

                <div className="questions-list">
                  {quiz.questions.map((q, idx) => (
                    <div
                      key={idx}
                      className={`question-card ${showResults ? (selectedAnswers[idx] === q.correct_answer ? 'correct' : 'incorrect') : ''}`}
                    >
                      <p className="question-text">
                        <strong>Q{idx + 1}.</strong> {q.question}
                      </p>
                      <div className="options-list">
                        {q.options.map((opt, optIdx) => {
                          const letter = String.fromCharCode(65 + optIdx);
                          const isSelected = selectedAnswers[idx] === letter;
                          const isCorrect = letter === q.correct_answer;

                          return (
                            <button
                              key={optIdx}
                              className={`option-btn ${isSelected ? 'selected' : ''} ${showResults && isCorrect ? 'correct' : ''} ${showResults && isSelected && !isCorrect ? 'incorrect' : ''}`}
                              onClick={() => selectAnswer(idx, letter)}
                            >
                              {opt}
                              {showResults && isCorrect && <CheckCircle size={16} />}
                              {showResults && isSelected && !isCorrect && <XCircle size={16} />}
                            </button>
                          );
                        })}
                      </div>
                      {showResults && (
                        <p className="explanation">
                          <strong>Explanation:</strong> {q.explanation}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                {!showResults && quiz.questions.length > 0 && (
                  <button
                    onClick={checkAnswers}
                    className="check-btn"
                    disabled={Object.keys(selectedAnswers).length < quiz.questions.length}
                  >
                    Check Answers
                  </button>
                )}
              </div>
            )}
          </div>
        </Panel>
      </PanelGroup>

      <style jsx>{`
        .study-container {
          height: 100vh;
          display: flex;
          flex-direction: column;
          background: var(--background);
          color: var(--text);
        }

        .study-loading, .study-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100vh;
          gap: 1rem;
          color: var(--text-muted);
          background: var(--background);
        }

        .study-panels {
          flex: 1;
          display: flex;
        }

        .pdf-panel, .quiz-panel {
          display: flex;
          flex-direction: column;
          background: var(--surface);
        }

        .pdf-header, .quiz-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem 1.5rem;
          border-bottom: 1px solid var(--border);
          background: var(--glass-bg);
          backdrop-filter: blur(12px);
        }

        .pdf-header h2, .quiz-header h2 {
          font-size: 1.1rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: var(--text);
        }

        .page-nav {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .page-nav button {
          padding: 0.5rem;
          background: var(--surface-hover);
          border: 1px solid var(--border);
          border-radius: 0.5rem;
          color: var(--text);
          cursor: pointer;
          transition: background 0.2s, border-color 0.2s;
        }

        .page-nav button:hover:not(:disabled) {
          background: var(--border);
          border-color: var(--border-light);
        }

        .page-nav button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .page-nav span {
          color: var(--text-muted);
          font-size: 0.9rem;
        }

        .pdf-viewer {
          flex: 1;
          overflow: auto;
          padding: 1rem;
          background: var(--background);
        }

        .resize-handle {
          width: 4px;
          background: var(--border);
          cursor: col-resize;
          transition: background 0.2s;
        }

        .resize-handle:hover {
          background: var(--primary);
        }

        .quiz-controls {
          display: flex;
          gap: 0.75rem;
          align-items: center;
        }

        .quiz-controls select {
          padding: 0.5rem 0.75rem;
          background: var(--surface-hover);
          border: 1px solid var(--border);
          border-radius: 0.5rem;
          color: var(--text);
          cursor: pointer;
        }

        .quiz-controls select:focus {
          outline: none;
          border-color: var(--primary);
        }

        .generate-btn {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: var(--primary);
          border: none;
          border-radius: 0.5rem;
          color: white;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s, transform 0.2s, box-shadow 0.2s;
        }

        .generate-btn:hover:not(:disabled) {
          background: var(--primary-hover);
          transform: translateY(-1px);
          box-shadow: var(--shadow-glow);
        }

        .generate-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .quiz-content {
          flex: 1;
          overflow: auto;
          padding: 1.5rem;
          background: var(--background);
        }

        .quiz-loading, .quiz-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          gap: 1rem;
          text-align: center;
          color: var(--text-dim);
        }

        .quiz-empty h3 {
          color: var(--text);
        }

        .quiz-container {
          max-width: 100%;
        }

        .quiz-title {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .quiz-title h3 {
          font-size: 1.25rem;
          color: var(--text);
        }

        .difficulty-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
        }

        .difficulty-badge.beginner {
          background: rgba(107, 143, 113, 0.15);
          color: var(--primary);
        }

        .difficulty-badge.intermediate {
          background: rgba(184, 146, 106, 0.15);
          color: var(--accent);
        }

        .difficulty-badge.advanced {
          background: rgba(220, 100, 100, 0.15);
          color: #dc6464;
        }

        .score-banner {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background: var(--primary);
          border-radius: 0.75rem;
          margin-bottom: 1.5rem;
          font-weight: 600;
          color: white;
        }

        .retry-btn {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: rgba(255,255,255,0.2);
          border: none;
          border-radius: 0.5rem;
          color: white;
          cursor: pointer;
          transition: background 0.2s;
        }

        .retry-btn:hover {
          background: rgba(255,255,255,0.3);
        }

        .questions-list {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .question-card {
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: 0.75rem;
          padding: 1.25rem;
          transition: border-color 0.2s, background 0.2s;
        }

        .question-card.correct {
          border-color: var(--primary);
          background: rgba(107, 143, 113, 0.08);
        }

        .question-card.incorrect {
          border-color: #dc6464;
          background: rgba(220, 100, 100, 0.08);
        }

        .question-text {
          margin-bottom: 1rem;
          line-height: 1.6;
          color: var(--text);
        }

        .options-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .option-btn {
          display: flex;
          justify-content: space-between;
          align-items: center;
          width: 100%;
          padding: 0.75rem 1rem;
          background: var(--surface-hover);
          border: 2px solid transparent;
          border-radius: 0.5rem;
          color: var(--text);
          text-align: left;
          cursor: pointer;
          transition: all 0.2s;
        }

        .option-btn:hover:not(.correct):not(.incorrect) {
          background: var(--border);
        }

        .option-btn.selected {
          border-color: var(--primary);
          background: rgba(107, 143, 113, 0.1);
        }

        .option-btn.correct {
          border-color: var(--primary);
          background: rgba(107, 143, 113, 0.15);
        }

        .option-btn.incorrect {
          border-color: #dc6464;
          background: rgba(220, 100, 100, 0.15);
        }

        .explanation {
          margin-top: 1rem;
          padding-top: 1rem;
          border-top: 1px solid var(--border);
          color: var(--text-muted);
          font-size: 0.9rem;
          line-height: 1.5;
        }

        .check-btn {
          width: 100%;
          padding: 1rem;
          margin-top: 1.5rem;
          background: var(--primary);
          border: none;
          border-radius: 0.75rem;
          color: white;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s, transform 0.2s, box-shadow 0.2s;
        }

        .check-btn:hover:not(:disabled) {
          background: var(--primary-hover);
          transform: translateY(-2px);
          box-shadow: var(--shadow-glow);
        }

        .check-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .quiz-tooltip {
          position: fixed;
          transform: translate(-50%, -100%);
          z-index: 1000;
        }

        .quiz-tooltip button {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: var(--primary);
          border: none;
          border-radius: 9999px;
          color: white;
          font-weight: 500;
          cursor: pointer;
          box-shadow: var(--shadow-lg);
          animation: popup 0.2s ease-out;
        }

        .quiz-tooltip button:hover {
          background: var(--primary-hover);
        }

        @keyframes popup {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
      `}</style>
    </div>
  );
}

// Page content component (fetches from backend)
function PageContent({ docId, pageNumber }: { docId: string; pageNumber: number }) {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchContent() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/documents/${docId}/page/${pageNumber}`);
        if (res.ok) {
          const data = await res.json();
          setContent(data.content);
        }
      } catch (err) {
        console.error('Failed to fetch page content');
      } finally {
        setLoading(false);
      }
    }
    fetchContent();
  }, [docId, pageNumber]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
        <Loader2 className="animate-spin" size={24} />
      </div>
    );
  }

  return (
    <div className="page-content" style={{
      background: 'var(--surface)',
      color: 'var(--text)',
      padding: '2rem',
      borderRadius: '0.75rem',
      minHeight: '100%',
      whiteSpace: 'pre-wrap',
      lineHeight: 1.8,
      fontFamily: 'Georgia, serif',
      border: '1px solid var(--border)',
      boxShadow: 'var(--shadow-sm)'
    }}>
      {content || 'No content available for this page.'}
    </div>
  );
}
