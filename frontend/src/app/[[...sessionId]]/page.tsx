"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { ChatContainer } from "@/components/chat";
import { ConnectionsDialog } from "@/components/ConnectionsDialog";
import { SettingsDialog } from "@/components/SettingsDialog";
import { DocumentPanel } from "@/components/DocumentPanel";
import { useTheme } from "@/store/useThemeStore";
import { useAppStore } from "@/store/useAppStore";
import {
    MessageSquare, Users, Settings, Plus,
    PanelLeft, Trash2
} from "lucide-react";

interface AttachedDocument {
    id: string;
    filename: string;
    page_count: number;
}

export default function ChatPage() {
    const params = useParams();
    const router = useRouter();
    const sessionId = params.sessionId?.[0] as string | undefined ?? null;

    const {
        sessions,
        isSidebarExpanded,
        isRecentsExpanded,
        setSidebarExpanded,
        setRecentsExpanded,
        loadSessions,
        deleteSession,
    } = useAppStore();

    const [isConnectionsOpen, setIsConnectionsOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0);

    // Document panel state
    const [attachedDoc, setAttachedDoc] = useState<AttachedDocument | null>(null);
    const [isPdfPanelOpen, setIsPdfPanelOpen] = useState(false);

    useTheme();

    useEffect(() => {
        loadSessions();
    }, [loadSessions]);

    const handleNewChat = () => {
        router.replace('/');
        setRefreshKey(prev => prev + 1);
        setAttachedDoc(null);
        setIsPdfPanelOpen(false);
    };

    const handleSessionSwitch = (newSessionId: string) => {
        router.replace(`/${newSessionId}`);
    };

    const handleSessionCreated = (newSessionId: string) => {
        // Navigate to new session but KEEP PDF panel open
        router.replace(`/${newSessionId}`);
        loadSessions();
        // Don't reset attachedDoc or isPdfPanelOpen here
    };

    const handleDeleteSession = async (id: string) => {
        const success = await deleteSession(id);
        if (success && sessionId === id) {
            router.replace('/');
            setRefreshKey(prev => prev + 1);
        }
    };

    const handleDocumentAttached = (doc: AttachedDocument) => {
        setAttachedDoc(doc);
        setIsPdfPanelOpen(true);
    };

    const handleQuizRequest = (page: number, difficulty: string, selectedText?: string) => {
        // Send quiz request to ChatContainer via custom event
        let quizPrompt: string;

        if (selectedText) {
            // Quiz from highlighted text
            quizPrompt = `Tạo quiz từ đoạn văn sau với độ khó ${difficulty}:\n\n"${selectedText.slice(0, 500)}${selectedText.length > 500 ? '...' : ''}"`;
        } else {
            // Quiz from entire page
            quizPrompt = `Tạo quiz cho trang ${page} của tài liệu "${attachedDoc?.filename}" với độ khó ${difficulty}. Document ID: ${attachedDoc?.id}`;
        }

        window.dispatchEvent(new CustomEvent('quizRequest', {
            detail: { prompt: quizPrompt, docId: attachedDoc?.id, page, difficulty, selectedText }
        }));
    };

    return (
        <div className="flex h-screen bg-[var(--background)] p-2 gap-2">
            {/* Sidebar */}
            <aside
                className={`flex flex-col bg-[var(--surface)] border border-[var(--border)] rounded-xl transition-all duration-200 ${isSidebarExpanded ? "w-64" : "w-16"}`}
            >
                {/* Sidebar header */}
                <div className="p-3">
                    {isSidebarExpanded ? (
                        <div className="flex items-center justify-between">
                            <button
                                onClick={() => setSidebarExpanded(false)}
                                className="w-10 h-10 rounded-lg flex items-center justify-center hover:bg-[var(--surface-hover)] cursor-pointer"
                                aria-label="Collapse sidebar"
                            >
                                <PanelLeft className="w-5 h-5 text-[var(--text-muted)]" />
                            </button>
                            <button
                                onClick={handleNewChat}
                                className="w-10 h-10 rounded-lg flex items-center justify-center hover:bg-[var(--surface-hover)] cursor-pointer"
                                aria-label="New chat"
                            >
                                <Plus className="w-5 h-5 text-[var(--text-muted)]" />
                            </button>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-1">
                            <button
                                onClick={() => setSidebarExpanded(true)}
                                className="w-10 h-10 rounded-lg flex items-center justify-center hover:bg-[var(--surface-hover)] cursor-pointer"
                                aria-label="Expand sidebar"
                            >
                                <PanelLeft className="w-5 h-5 text-[var(--text-muted)]" />
                            </button>
                            <button
                                onClick={handleNewChat}
                                className="w-10 h-10 rounded-lg flex items-center justify-center hover:bg-[var(--surface-hover)] cursor-pointer"
                                aria-label="New chat"
                            >
                                <Plus className="w-5 h-5 text-[var(--text-muted)]" />
                            </button>
                        </div>
                    )}
                </div>

                {/* Chat history */}
                {isSidebarExpanded && (
                    <div className="flex-1 flex flex-col min-h-0 px-2 py-1">
                        {/* Recents header */}
                        <button
                            onClick={() => setRecentsExpanded(!isRecentsExpanded)}
                            className="flex items-center justify-between px-3 py-2 text-xs text-[var(--text-dim)] hover:text-[var(--text-muted)] cursor-pointer"
                        >
                            <span>Recents</span>
                            <span>{isRecentsExpanded ? 'Hide' : 'Show'}</span>
                        </button>

                        {/* Chat list */}
                        <div className={`chat-history-content sidebar-scroll flex-1 overflow-y-auto ${isRecentsExpanded ? 'expanded' : 'collapsed'}`}>
                            {sessions.length === 0 ? (
                                <p className="text-xs text-[var(--text-dim)] px-3 py-4 text-center">
                                    No chat history yet
                                </p>
                            ) : (
                                <div className="space-y-0.5">
                                    {sessions.slice(0, 10).map((session) => (
                                        <div
                                            key={session.id}
                                            className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer ${sessionId === session.id
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
                                                className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-[var(--background)] cursor-pointer"
                                                aria-label="Delete session"
                                            >
                                                <Trash2 className="w-3.5 h-3.5 text-[var(--text-dim)] hover:text-red-500" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Bottom actions */}
                <div className={`border-t border-[var(--border)] mt-auto ${isSidebarExpanded ? "p-2 space-y-0.5" : "p-3 flex flex-col items-center gap-1"}`}>
                    {/* Connections */}
                    <button
                        onClick={() => setIsConnectionsOpen(true)}
                        className={`flex items-center rounded-lg hover:bg-[var(--surface-hover)] cursor-pointer text-[var(--text-muted)] ${isSidebarExpanded ? "w-full gap-2.5 px-3 py-2.5" : "w-10 h-10 justify-center"}`}
                        title="Connections"
                        aria-label="Connections"
                    >
                        <Users className="w-5 h-5" />
                        {isSidebarExpanded && <span className="text-sm">Connections</span>}
                    </button>

                    {/* Settings */}
                    <button
                        onClick={() => setIsSettingsOpen(true)}
                        className={`flex items-center rounded-lg hover:bg-[var(--surface-hover)] cursor-pointer text-[var(--text-muted)] ${isSidebarExpanded ? "w-full gap-2.5 px-3 py-2.5" : "w-10 h-10 justify-center"}`}
                        aria-label="Settings"
                    >
                        <Settings className="w-5 h-5" />
                        {isSidebarExpanded && <span className="text-sm">Settings</span>}
                    </button>
                </div>
            </aside>

            {/* Main content with split layout */}
            <main className="flex-1 flex bg-[var(--surface)] rounded-xl border border-[var(--border)] overflow-hidden">
                <PanelGroup direction="horizontal" id="main-panel-group">
                    {/* PDF Panel - on the left when open */}
                    {isPdfPanelOpen && attachedDoc && (
                        <>
                            <Panel id="pdf-panel" defaultSize={50} minSize={30} order={1}>
                                <DocumentPanel
                                    docId={attachedDoc.id}
                                    filename={attachedDoc.filename}
                                    pageCount={attachedDoc.page_count}
                                    onClose={() => setIsPdfPanelOpen(false)}
                                />
                            </Panel>

                            <PanelResizeHandle
                                id="resize-handle"
                                className="group w-2 bg-[var(--border)] hover:bg-[var(--primary)] transition-colors cursor-col-resize relative flex items-center justify-center"
                            >
                                {/* Grip dots */}
                                <div className="flex flex-col gap-1 opacity-50 group-hover:opacity-100 transition-opacity">
                                    <div className="w-1 h-1 rounded-full bg-[var(--text-dim)]" />
                                    <div className="w-1 h-1 rounded-full bg-[var(--text-dim)]" />
                                    <div className="w-1 h-1 rounded-full bg-[var(--text-dim)]" />
                                </div>
                            </PanelResizeHandle>
                        </>
                    )}

                    {/* Chat Panel - on the right (or full width if no PDF) */}
                    <Panel id="chat-panel" defaultSize={isPdfPanelOpen ? 50 : 100} minSize={35} order={2}>
                        <div className="h-full overflow-hidden">
                            <ChatContainer
                                key={`${sessionId ?? 'new'}-${refreshKey}`}
                                sessionId={sessionId}
                                onMessagesChange={loadSessions}
                                onSessionCreated={handleSessionCreated}
                                onDocumentAttached={handleDocumentAttached}
                                attachedDocId={attachedDoc?.id}
                            />
                        </div>
                    </Panel>
                </PanelGroup>
            </main>

            <ConnectionsDialog
                isOpen={isConnectionsOpen}
                onClose={() => setIsConnectionsOpen(false)}
            />

            <SettingsDialog
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
            />
        </div>
    );
}
