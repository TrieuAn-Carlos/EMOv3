"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChatContainer } from "@/components/chat";
import { ConnectionsDialog } from "@/components/ConnectionsDialog";
import { SettingsDialog } from "@/components/SettingsDialog";
import { useTheme } from "@/store/useThemeStore";
import {
    MessageSquare, Mail, Settings, Plus,
    RotateCcw, ChevronLeft, ChevronRight, Trash2
} from "lucide-react";

interface ChatSession {
    id: string;
    title: string;
    created_at: string;
    message_count: number;

}

export default function ChatPage() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.sessionId as string;

    const [isConnectionsOpen, setIsConnectionsOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isSidebarExpanded, setIsSidebarExpanded] = useState(true); // Auto-expand on session page
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [refreshKey, setRefreshKey] = useState(0);

    // Initialize theme
    useTheme();

    // Load sessions from backend
    useEffect(() => {
        loadSessions();
    }, []);

    const loadSessions = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/chat/sessions');
            if (response.ok) {
                const data = await response.json();
                setSessions(data.sessions || []);
            }
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    };

    const handleNewChat = () => {
        router.push('/');
    };

    const handleRestart = () => {
        setRefreshKey(prev => prev + 1);
    };

    const handleMessagesChange = async () => {
        await loadSessions();
    };

    const handleSessionSwitch = (newSessionId: string) => {
        router.push(`/chat/${newSessionId}`);
    };

    const handleDeleteSession = async (id: string) => {
        try {
            const response = await fetch(`http://localhost:8000/api/chat/sessions/${id}`, {
                method: 'DELETE',
            });

            if (response.ok) {
                setSessions(sessions.filter(s => s.id !== id));
                if (sessionId === id) {
                    router.push('/');
                }
            }
        } catch (error) {
            console.error('Failed to delete session:', error);
        }
    };

    return (
        <div className="flex h-screen bg-[var(--background)] p-3 gap-3">
            {/* Sidebar */}
            <aside
                className={`flex flex-col bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-md transition-all duration-300 ${isSidebarExpanded ? "w-64" : "w-16"
                    }`}
            >
                {/* Top section */}
                <div className="flex items-center justify-between p-3 border-b border-[var(--border)]">
                    {isSidebarExpanded && (
                        <button
                            onClick={() => setIsSidebarExpanded(false)}
                            className="p-1.5 rounded-lg hover:bg-[var(--surface-hover)] transition-all cursor-pointer"
                            aria-label="Collapse sidebar"
                        >
                            <ChevronLeft className="w-4 h-4 text-[var(--text-muted)]" />
                        </button>
                    )}
                </div>

                {/* New chat button */}
                <div className="p-3">
                    <button
                        onClick={handleNewChat}
                        className={`flex items-center gap-2.5 rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] transition-all cursor-pointer shadow-sm hover:shadow-md ${isSidebarExpanded ? "w-full px-4 py-2.5" : "w-10 h-10 justify-center"
                            }`}
                        aria-label="New chat"
                    >
                        <Plus className="w-4 h-4" />
                        {isSidebarExpanded && (
                            <span className="text-sm font-medium">New Chat</span>
                        )}
                    </button>
                </div>

                {/* Chat history */}
                {isSidebarExpanded && (
                    <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
                        {sessions.length === 0 ? (
                            <p className="text-xs text-[var(--text-dim)] px-3 py-8 text-center">
                                No chat history yet
                            </p>
                        ) : (
                            sessions.slice(0, 10).map((session) => (
                                <div
                                    key={session.id}
                                    className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${sessionId === session.id
                                        ? "bg-[var(--surface-hover)] text-[var(--text)]"
                                        : "hover:bg-[var(--surface-hover)] text-[var(--text-muted)]"
                                        }`}
                                    onClick={() => handleSessionSwitch(session.id)}
                                >
                                    <MessageSquare className="w-4 h-4 flex-shrink-0" />
                                    <span className="text-sm truncate flex-1">
                                        {session.title}
                                    </span>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteSession(session.id);
                                        }}
                                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-[var(--background)] transition-all cursor-pointer"
                                        aria-label="Delete session"
                                    >
                                        <Trash2 className="w-3.5 h-3.5 text-[var(--text-dim)] hover:text-red-500" />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {/* Toggle expand */}
                {!isSidebarExpanded && (
                    <div className="p-2">
                        <button
                            onClick={() => setIsSidebarExpanded(true)}
                            className="w-10 h-10 rounded-lg flex items-center justify-center hover:bg-[var(--surface-hover)] transition-all cursor-pointer"
                            aria-label="Expand sidebar"
                        >
                            <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                        </button>
                    </div>
                )}

                {/* Spacer */}
                <div className="flex-1" />

                {/* Bottom actions */}
                <div className="p-2 space-y-0.5 border-t border-[var(--border)] mt-auto">
                    {/* Connections */}
                    <button
                        onClick={() => setIsConnectionsOpen(true)}
                        className={`flex items-center gap-2.5 rounded-lg hover:bg-[var(--surface-hover)] transition-all cursor-pointer ${isSidebarExpanded ? "w-full px-3 py-2.5 text-[var(--text-muted)]" : "w-10 h-10 justify-center"
                            }`}
                        title="Connections"
                        aria-label="Connections"
                    >
                        <Mail className="w-4 h-4" />
                        {isSidebarExpanded && (
                            <span className="text-sm">Connections</span>
                        )}
                    </button>

                    {/* Settings */}
                    <button
                        onClick={() => setIsSettingsOpen(true)}
                        className={`flex items-center gap-2.5 rounded-lg hover:bg-[var(--surface-hover)] transition-all cursor-pointer ${isSidebarExpanded ? "w-full px-3 py-2.5 text-[var(--text-muted)]" : "w-10 h-10 justify-center"
                            }`}
                        aria-label="Settings"
                    >
                        <Settings className="w-4 h-4" />
                        {isSidebarExpanded && (
                            <span className="text-sm">Settings</span>
                        )}
                    </button>
                </div>
            </aside>

            {/* Main content */}
            <main className="flex-1 flex flex-col bg-[var(--surface)] rounded-2xl border border-[var(--border)] shadow-md overflow-hidden">
                {/* Header */}
                <header className="h-14 px-6 flex items-center justify-between border-b border-[var(--border)] bg-[var(--background)]/50 backdrop-blur-sm">
                    <div className="flex items-center gap-2.5">
                        <span className="text-base font-semibold text-[var(--text)]">EMO</span>
                        <span className="px-2 py-0.5 text-[10px] rounded-md bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] text-white font-semibold tracking-wide">
                            AI
                        </span>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="text-xs text-[var(--text-muted)] font-medium">Gemini 2.5 Flash Lite</span>
                        <button
                            onClick={handleRestart}
                            className="p-2 rounded-lg hover:bg-[var(--surface-hover)] transition-all cursor-pointer"
                            title="Restart chat"
                            aria-label="Restart chat"
                        >
                            <RotateCcw className="w-4 h-4 text-[var(--text-muted)]" />
                        </button>
                    </div>
                </header>

                {/* Chat area */}
                <div className="flex-1 overflow-hidden">
                    <ChatContainer
                        key={refreshKey}
                        sessionId={sessionId}
                        onMessagesChange={handleMessagesChange}
                    />
                </div>
            </main>

            {/* Connections Dialog */}
            <ConnectionsDialog
                isOpen={isConnectionsOpen}
                onClose={() => setIsConnectionsOpen(false)}
            />

            {/* Settings Dialog */}
            <SettingsDialog
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
            />
        </div>
    );
}
