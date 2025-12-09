"use client";

import { X } from "lucide-react";
import { useTheme, ThemeMode } from "@/store/useThemeStore";
import { useEffect } from "react";

interface SettingsDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

export function SettingsDialog({ isOpen, onClose }: SettingsDialogProps) {
    const { mode, setMode } = useTheme();

    // Close on ESC key
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        if (isOpen) {
            document.addEventListener("keydown", handleEsc);
            return () => document.removeEventListener("keydown", handleEsc);
        }
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const themeOptions: { value: ThemeMode; label: string; description: string }[] = [
        {
            value: "light",
            label: "Light",
            description: "Bright and clean interface"
        },
        {
            value: "dark",
            label: "Dark",
            description: "Easy on the eyes"
        },
        {
            value: "system",
            label: "System",
            description: "Follow system preference"
        }
    ];

    return (
        <div
            className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 px-4 animate-fade-in"
            onClick={onClose}
        >
            <div
                className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-slide-in"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--background)]/50 backdrop-blur-sm">
                    <h2 className="text-lg font-semibold text-[var(--text)]">Settings</h2>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-[var(--surface-hover)] transition-colors cursor-pointer"
                        aria-label="Close"
                    >
                        <X className="w-5 h-5 text-[var(--text-muted)]" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Theme Section */}
                    <div>
                        <h3 className="text-sm font-semibold text-[var(--text)] mb-3">Appearance</h3>
                        <div className="space-y-2.5">
                            {(['system', 'light', 'dark'] as const).map((themeOption) => (
                                <label
                                    key={themeOption}
                                    className="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all hover:bg-[var(--surface-hover)] group"
                                >
                                    <input
                                        type="radio"
                                        name="theme"
                                        value={themeOption}
                                        checked={mode === themeOption}
                                        onChange={() => setMode(themeOption)}
                                        className="w-4 h-4 text-[var(--primary)] cursor-pointer"
                                    />
                                    <span className="text-sm text-[var(--text-muted)] group-hover:text-[var(--text)] transition-colors capitalize">
                                        {themeOption}
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
