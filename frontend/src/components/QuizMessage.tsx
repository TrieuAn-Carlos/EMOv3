'use client';

import { useState } from 'react';
import { Check, X, ChevronRight, Trophy, RotateCcw } from 'lucide-react';
import { MarkdownRenderer } from './chat/MarkdownRenderer';

interface QuizQuestion {
    type?: string;
    question: string;
    options: string[];
    correct_answer: string;
    explanation: string;
}

interface QuizMessageProps {
    title: string;
    difficulty: string;
    questions: QuizQuestion[];
}

export function QuizMessage({ title, difficulty, questions }: QuizMessageProps) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [selected, setSelected] = useState<string | null>(null);
    const [answered, setAnswered] = useState(false);
    const [score, setScore] = useState(0);
    const [complete, setComplete] = useState(false);

    if (!questions || questions.length === 0) {
        return (
            <div className="p-4 bg-[var(--surface)] rounded-xl border border-[var(--border)]">
                <p className="text-[var(--text-muted)]">Không thể tạo quiz từ nội dung này.</p>
            </div>
        );
    }

    const current = questions[currentIndex];
    const total = questions.length;

    const handleSelect = (opt: string) => {
        if (answered) return;
        setSelected(opt);
        setAnswered(true);

        const optLetter = opt.charAt(0).toUpperCase();
        const correctLetter = current.correct_answer.charAt(0).toUpperCase();
        if (optLetter === correctLetter || opt.toLowerCase() === current.correct_answer.toLowerCase()) {
            setScore(s => s + 1);
        }
    };

    const handleNext = () => {
        if (currentIndex < total - 1) {
            setCurrentIndex(i => i + 1);
            setSelected(null);
            setAnswered(false);
        } else {
            setComplete(true);
        }
    };

    const restart = () => {
        setCurrentIndex(0);
        setSelected(null);
        setAnswered(false);
        setScore(0);
        setComplete(false);
    };

    const getStyle = (opt: string) => {
        const optLetter = opt.charAt(0).toUpperCase();
        const correctLetter = current.correct_answer.charAt(0).toUpperCase();
        const isCorrect = optLetter === correctLetter || opt.toLowerCase() === current.correct_answer.toLowerCase();
        const isSelected = selected === opt;

        if (!answered) {
            return isSelected
                ? 'border-[var(--primary)] bg-[var(--primary)]/10'
                : 'border-[var(--border)] hover:border-[var(--primary)]/50';
        }
        if (isCorrect) return 'border-green-500 bg-green-500/10';
        if (isSelected) return 'border-red-500 bg-red-500/10';
        return 'border-[var(--border)] opacity-50';
    };

    // Completion screen
    if (complete) {
        const pct = Math.round((score / total) * 100);
        const grade = pct >= 80 ? 'Xuất sắc!' : pct >= 60 ? 'Tốt!' : 'Cần cải thiện';
        const color = pct >= 80 ? 'text-green-500' : pct >= 60 ? 'text-blue-500' : 'text-orange-500';

        return (
            <div className="p-4 bg-[var(--surface)] rounded-xl border border-[var(--border)]">
                <div className="text-center">
                    <Trophy className={`w-10 h-10 mx-auto mb-2 ${color}`} />
                    <p className={`text-lg font-bold ${color}`}>{grade}</p>
                    <p className="text-2xl font-bold text-[var(--text)]">{score}/{total}</p>
                    <p className="text-sm text-[var(--text-muted)]">({pct}% chính xác)</p>
                    <button
                        onClick={restart}
                        className="mt-3 flex items-center gap-2 mx-auto px-3 py-1.5 bg-[var(--surface-hover)] rounded-lg text-sm hover:bg-[var(--border)] transition-colors"
                    >
                        <RotateCcw className="w-4 h-4" />
                        Làm lại
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
            {/* Header */}
            <div className="px-4 py-2 bg-[var(--surface-hover)] border-b border-[var(--border)]">
                <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--text-dim)]">{difficulty}</span>
                    <span className="text-xs text-[var(--text-muted)]">{currentIndex + 1}/{total}</span>
                </div>
                <p className="text-sm font-medium text-[var(--text)] truncate mt-0.5">{title}</p>
                {/* Progress */}
                <div className="mt-2 h-1 bg-[var(--border)] rounded-full">
                    <div
                        className="h-full bg-[var(--primary)] rounded-full transition-all"
                        style={{ width: `${((currentIndex + 1) / total) * 100}%` }}
                    />
                </div>
            </div>

            {/* Question */}
            <div className="p-4">
                <div className="text-[var(--text)] font-medium mb-3">
                    <MarkdownRenderer content={current.question} />
                </div>

                <div className="space-y-2">
                    {current.options.map((opt, i) => (
                        <button
                            key={i}
                            onClick={() => handleSelect(opt)}
                            disabled={answered}
                            className={`w-full p-2.5 text-left rounded-lg border-2 transition-all text-sm ${getStyle(opt)}`}
                        >
                            <div className="flex items-center justify-between">
                                <span className="text-[var(--text)] flex-1">
                                    <MarkdownRenderer content={opt} />
                                </span>
                                {answered && (
                                    <>
                                        {(opt.charAt(0).toUpperCase() === current.correct_answer.charAt(0).toUpperCase()) && (
                                            <Check className="w-4 h-4 text-green-500" />
                                        )}
                                        {selected === opt && opt.charAt(0).toUpperCase() !== current.correct_answer.charAt(0).toUpperCase() && (
                                            <X className="w-4 h-4 text-red-500" />
                                        )}
                                    </>
                                )}
                            </div>
                        </button>
                    ))}
                </div>

                {/* Explanation */}
                {answered && current.explanation && (
                    <div className="mt-3 p-2.5 bg-[var(--background)] rounded-lg text-sm">
                        <p className="text-xs text-[var(--text-dim)] mb-1">Giải thích:</p>
                        <div className="text-[var(--text-muted)]">
                            <MarkdownRenderer content={current.explanation} />
                        </div>
                    </div>
                )}

                {/* Next button */}
                {answered && (
                    <button
                        onClick={handleNext}
                        className="mt-3 w-full flex items-center justify-center gap-2 py-2 bg-[var(--primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--primary-hover)] transition-colors"
                    >
                        {currentIndex < total - 1 ? (
                            <>Tiếp theo <ChevronRight className="w-4 h-4" /></>
                        ) : (
                            <>Xem kết quả <Trophy className="w-4 h-4" /></>
                        )}
                    </button>
                )}
            </div>
        </div>
    );
}
