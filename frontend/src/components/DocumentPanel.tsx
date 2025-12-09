'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import {
    X,
    ChevronLeft,
    ChevronRight,
    Brain,
    Loader2,
    ZoomIn,
    ZoomOut,
    Maximize
} from 'lucide-react';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const API_BASE = 'http://localhost:8000/api';

interface DocumentPanelProps {
    docId: string;
    filename: string;
    pageCount: number;
    onClose: () => void;
}

export function DocumentPanel({
    docId,
    filename,
    pageCount,
    onClose
}: DocumentPanelProps) {
    const [currentPage, setCurrentPage] = useState(1);
    const [numPages, setNumPages] = useState<number>(pageCount);
    const [scale, setScale] = useState(0.8);
    const [loading, setLoading] = useState(true);
    const [difficulty, setDifficulty] = useState('Beginner');
    const [pageWidth, setPageWidth] = useState<number | null>(null);
    const [containerWidth, setContainerWidth] = useState<number>(0);
    const [quizLoading, setQuizLoading] = useState(false);

    const containerRef = useRef<HTMLDivElement>(null);

    // Text selection state
    const [selectedText, setSelectedText] = useState('');
    const [showTooltip, setShowTooltip] = useState(false);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

    const pdfUrl = `${API_BASE}/documents/${docId}/file`;

    // Auto-fit to container width
    const fitToWidth = useCallback(() => {
        if (containerWidth > 0 && pageWidth) {
            const availableWidth = containerWidth - 32;
            const newScale = availableWidth / pageWidth;
            setScale(Math.min(Math.max(newScale, 0.4), 1.2));
        }
    }, [pageWidth, containerWidth]);

    // Watch container resize
    useEffect(() => {
        if (!containerRef.current) return;

        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                setContainerWidth(entry.contentRect.width);
            }
        });

        resizeObserver.observe(containerRef.current);
        return () => resizeObserver.disconnect();
    }, []);

    // Auto-fit when container or page width changes
    useEffect(() => {
        if (pageWidth && containerWidth > 0) {
            fitToWidth();
        }
    }, [pageWidth, containerWidth, fitToWidth]);

    // Handle text selection - only within PDF
    const handleTextSelection = useCallback(() => {
        const selection = window.getSelection();
        if (!selection || !containerRef.current) {
            setShowTooltip(false);
            return;
        }

        // Check if selection is within PDF container
        const anchorNode = selection.anchorNode;
        if (!anchorNode || !containerRef.current.contains(anchorNode)) {
            setShowTooltip(false);
            setSelectedText('');
            return;
        }

        const text = selection.toString().trim();
        if (text.length > 20) {
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
            setSelectedText('');
        }
    }, []);

    useEffect(() => {
        document.addEventListener('mouseup', handleTextSelection);
        return () => document.removeEventListener('mouseup', handleTextSelection);
    }, [handleTextSelection]);

    const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
        setLoading(false);
    };

    const onPageLoadSuccess = ({ width }: { width: number }) => {
        if (!pageWidth) {
            setPageWidth(width);
        }
    };

    // Send quiz request to chat
    const sendQuizToChat = (text?: string) => {
        setShowTooltip(false);
        setQuizLoading(true);
        window.getSelection()?.removeAllRanges();

        // Dispatch event for ChatContainer to handle
        window.dispatchEvent(new CustomEvent('quizRequest', {
            detail: {
                docId,
                page: currentPage,
                difficulty,
                selectedText: text || selectedText,
                isPageQuiz: !text && !selectedText
            }
        }));

        setSelectedText('');
        setTimeout(() => setQuizLoading(false), 500);
    };

    return (
        <div className="h-full flex flex-col bg-[var(--background)] border-r border-[var(--border)] relative">
            {/* Quiz Me Tooltip */}
            {showTooltip && (
                <div
                    className="fixed z-50"
                    style={{
                        left: tooltipPosition.x,
                        top: tooltipPosition.y,
                        transform: 'translate(-50%, -100%)'
                    }}
                >
                    <button
                        onClick={() => sendQuizToChat()}
                        className="flex items-center gap-2 px-4 py-2 bg-[var(--primary)] text-white rounded-full text-sm font-medium shadow-lg hover:bg-[var(--primary-hover)] transition-all animate-fade-in"
                    >
                        <Brain className="w-4 h-4" />
                        Quiz đoạn này
                    </button>
                </div>
            )}

            {/* Controls */}
            <div className="flex items-center justify-between px-3 py-2 bg-[var(--surface)] border-b border-[var(--border)]">
                {/* Page Navigation */}
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage <= 1}
                        className="p-1.5 rounded-lg bg-[var(--surface-hover)] hover:bg-[var(--border)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                        <ChevronLeft className="w-4 h-4 text-[var(--text)]" />
                    </button>
                    <span className="text-sm text-[var(--text-muted)] min-w-[60px] text-center">
                        {currentPage}/{numPages}
                    </span>
                    <button
                        onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))}
                        disabled={currentPage >= numPages}
                        className="p-1.5 rounded-lg bg-[var(--surface-hover)] hover:bg-[var(--border)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                        <ChevronRight className="w-4 h-4 text-[var(--text)]" />
                    </button>
                </div>

                {/* Zoom Controls */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setScale(s => Math.max(0.4, s - 0.1))}
                        className="p-1 rounded hover:bg-[var(--surface-hover)] text-[var(--text-muted)]"
                    >
                        <ZoomOut className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-xs text-[var(--text-dim)] w-10 text-center">
                        {Math.round(scale * 100)}%
                    </span>
                    <button
                        onClick={() => setScale(s => Math.min(2, s + 0.1))}
                        className="p-1 rounded hover:bg-[var(--surface-hover)] text-[var(--text-muted)]"
                    >
                        <ZoomIn className="w-3.5 h-3.5" />
                    </button>
                    <button
                        onClick={fitToWidth}
                        className="p-1 rounded hover:bg-[var(--surface-hover)] text-[var(--text-muted)] ml-1"
                    >
                        <Maximize className="w-3.5 h-3.5" />
                    </button>
                </div>

                {/* Quiz & Close */}
                <div className="flex items-center gap-2">
                    <select
                        value={difficulty}
                        onChange={(e) => setDifficulty(e.target.value)}
                        className="text-xs px-2 py-1 bg-[var(--surface-hover)] border border-[var(--border)] rounded text-[var(--text)] cursor-pointer"
                    >
                        <option value="Beginner">Dễ</option>
                        <option value="Intermediate">TB</option>
                        <option value="Advanced">Khó</option>
                    </select>
                    <button
                        onClick={() => sendQuizToChat()}
                        disabled={quizLoading}
                        className="flex items-center gap-1 px-2 py-1 bg-[var(--primary)] text-white rounded text-xs font-medium hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50"
                    >
                        {quizLoading ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                            <Brain className="w-3 h-3" />
                        )}
                        Quiz
                    </button>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] text-[var(--text-muted)]"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* PDF Viewer */}
            <div ref={containerRef} className="flex-1 overflow-auto p-4 flex justify-center">
                {loading && (
                    <div className="flex items-center justify-center h-full">
                        <Loader2 className="w-8 h-8 text-[var(--text-dim)] animate-spin" />
                    </div>
                )}

                <Document
                    file={pdfUrl}
                    onLoadSuccess={onDocumentLoadSuccess}
                    onLoadError={(error) => console.error('PDF load error:', error)}
                    loading={
                        <div className="flex items-center justify-center h-64">
                            <Loader2 className="w-8 h-8 text-[var(--text-dim)] animate-spin" />
                        </div>
                    }
                    className="pdf-document"
                >
                    <Page
                        pageNumber={currentPage}
                        scale={scale}
                        onLoadSuccess={onPageLoadSuccess}
                        renderTextLayer={true}
                        renderAnnotationLayer={true}
                        className="pdf-page shadow-lg rounded-lg overflow-hidden"
                    />
                </Document>
            </div>

            <style jsx global>{`
                .pdf-document {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                
                .pdf-page {
                    background: white !important;
                }
                
                .pdf-page canvas {
                    border-radius: 0.5rem;
                }
                
                .react-pdf__Page__textContent {
                    user-select: text !important;
                    cursor: text;
                }
                
                .react-pdf__Page__textContent span {
                    user-select: text !important;
                }
                
                .react-pdf__Page__textContent span::selection {
                    background: rgba(107, 143, 113, 0.3);
                }
            `}</style>
        </div>
    );
}
