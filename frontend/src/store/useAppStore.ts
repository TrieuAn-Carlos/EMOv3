"use client";

import { create } from 'zustand';

interface ChatSession {
    id: string;
    title: string;
    created_at: string;
    message_count: number;
}

interface AppStore {
    sessions: ChatSession[];
    isSidebarExpanded: boolean;
    isRecentsExpanded: boolean;
    setSessions: (sessions: ChatSession[]) => void;
    setSidebarExpanded: (expanded: boolean) => void;
    setRecentsExpanded: (expanded: boolean) => void;
    loadSessions: () => Promise<void>;
    deleteSession: (id: string) => Promise<boolean>;
}

export const useAppStore = create<AppStore>((set, get) => ({
    sessions: [],
    isSidebarExpanded: true,
    isRecentsExpanded: true,
    setSessions: (sessions) => set({ sessions }),
    setSidebarExpanded: (expanded) => set({ isSidebarExpanded: expanded }),
    setRecentsExpanded: (expanded) => set({ isRecentsExpanded: expanded }),

    loadSessions: async () => {
        try {
            const response = await fetch('http://localhost:8000/api/chat/sessions');
            if (response.ok) {
                const data = await response.json();
                set({ sessions: data.sessions || [] });
            }
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    },

    deleteSession: async (id: string) => {
        try {
            const response = await fetch(`http://localhost:8000/api/chat/sessions/${id}`, {
                method: 'DELETE',
            });
            if (response.ok) {
                set({ sessions: get().sessions.filter(s => s.id !== id) });
                return true;
            }
        } catch (error) {
            console.error('Failed to delete session:', error);
        }
        return false;
    },
}));
