"use client";

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useEffect } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

interface ThemeStore {
    mode: ThemeMode;
    resolvedTheme: ResolvedTheme;
    setMode: (mode: ThemeMode) => void;
    setResolvedTheme: (theme: ResolvedTheme) => void;
}

export const useThemeStore = create<ThemeStore>()(
    persist(
        (set) => ({
            mode: 'system',
            resolvedTheme: 'dark',
            setMode: (mode) => set({ mode }),
            setResolvedTheme: (theme) => set({ resolvedTheme: theme }),
        }),
        {
            name: 'emo-theme-storage',
            partialize: (state) => ({ mode: state.mode }),
        }
    )
);

// Hook to initialize and manage theme
export function useTheme() {
    const { mode, resolvedTheme, setMode, setResolvedTheme } = useThemeStore();

    useEffect(() => {
        const getSystemTheme = (): ResolvedTheme => {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        };

        const updateTheme = () => {
            const newResolvedTheme = mode === 'system' ? getSystemTheme() : mode;
            setResolvedTheme(newResolvedTheme);
            document.documentElement.setAttribute('data-theme', newResolvedTheme);
        };

        // Initial theme setup
        updateTheme();

        // Listen for system theme changes
        if (mode === 'system') {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const handleChange = () => updateTheme();

            // Modern browsers
            mediaQuery.addEventListener('change', handleChange);

            return () => {
                mediaQuery.removeEventListener('change', handleChange);
            };
        }
    }, [mode, setResolvedTheme]);

    return {
        mode,
        resolvedTheme,
        setMode,
    };
}
