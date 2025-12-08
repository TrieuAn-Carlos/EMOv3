"use client";

import { X, Mail, Calendar, Check, Loader2, Lightbulb, ExternalLink, RefreshCw, XCircle } from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";

interface ConnectionsDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

type ConnectionState = "idle" | "loading" | "connected" | "error" | "timeout";

interface ErrorDetails {
    title: string;
    message: string;
    suggestion: string;
}

export function ConnectionsDialog({ isOpen, onClose }: ConnectionsDialogProps) {
    const [gmailStatus, setGmailStatus] = useState<ConnectionState>("idle");
    const [calendarStatus, setCalendarStatus] = useState<ConnectionState>("idle");
    const [gmailError, setGmailError] = useState<ErrorDetails | null>(null);
    const [calendarError, setCalendarError] = useState<ErrorDetails | null>(null);
    const [message, setMessage] = useState<string | null>(null);
    const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Check actual connection status
    const checkConnectionStatus = useCallback(async () => {
        try {
            const response = await fetch("http://localhost:8000/api/auth/status");
            if (response.ok) {
                const data = await response.json();
                if (data.gmail && gmailStatus === "loading") {
                    setGmailStatus("connected");
                    setGmailError(null);
                    setMessage(null);
                } else if (!data.gmail && gmailStatus !== "loading" && gmailStatus !== "error" && gmailStatus !== "timeout") {
                    setGmailStatus("idle");
                }
                if (data.calendar && calendarStatus === "loading") {
                    setCalendarStatus("connected");
                    setCalendarError(null);
                    setMessage(null);
                } else if (!data.calendar && calendarStatus !== "loading" && calendarStatus !== "error" && calendarStatus !== "timeout") {
                    setCalendarStatus("idle");
                }
            }
        } catch (e) {
            console.error("Failed to check connection status:", e);
        }
    }, [gmailStatus, calendarStatus]);

    // Check status on open
    useEffect(() => {
        if (isOpen) {
            checkConnectionStatus();
        }
        return () => {
            if (pollTimeoutRef.current) {
                clearTimeout(pollTimeoutRef.current);
            }
        };
    }, [isOpen, checkConnectionStatus]);

    // Poll for status when OAuth is in progress
    useEffect(() => {
        let interval: NodeJS.Timeout | null = null;
        if (gmailStatus === "loading" || calendarStatus === "loading") {
            interval = setInterval(checkConnectionStatus, 2000);
        }
        return () => {
            if (interval) clearInterval(interval);
        };
    }, [gmailStatus, calendarStatus, checkConnectionStatus]);

    const handleGmailConnect = async () => {
        setGmailStatus("loading");
        setGmailError(null);
        setMessage("Check your browser - a Google login window should open...");

        try {
            const response = await fetch("http://localhost:8000/api/auth/gmail/connect");

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.status === "already_connected") {
                setGmailStatus("connected");
                setMessage(null);
            } else if (data.status === "started" || data.status === "in_progress") {
                setMessage(data.message || "Complete authorization in the browser window...");

                // Set timeout - if not connected after 2 minutes, show error
                pollTimeoutRef.current = setTimeout(() => {
                    if (gmailStatus === "loading") {
                        setGmailStatus("timeout");
                        setGmailError({
                            title: "Authorization Timeout",
                            message: "The authorization window may have been closed or blocked.",
                            suggestion: "Try again and complete the Google login process."
                        });
                        setMessage(null);
                    }
                }, 120000);
            } else {
                throw new Error("Unexpected response from server");
            }
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Unknown error";
            setGmailError({
                title: "Connection Failed",
                message: errorMessage.includes("credentials")
                    ? "OAuth credentials not configured on server"
                    : errorMessage.includes("fetch") || errorMessage.includes("network")
                        ? "Cannot reach backend server"
                        : errorMessage,
                suggestion: errorMessage.includes("credentials")
                    ? "Ensure credentials.json is properly configured."
                    : errorMessage.includes("fetch") || errorMessage.includes("network")
                        ? "Make sure the backend is running on port 8000."
                        : "Check the browser console and backend logs for details."
            });
            setGmailStatus("error");
            setMessage(null);
        }
    };

    const handleCalendarConnect = async () => {
        setCalendarStatus("loading");
        setCalendarError(null);
        setMessage("Check your browser - a Google login window should open...");

        try {
            const response = await fetch("http://localhost:8000/api/auth/calendar/connect");

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.status === "already_connected") {
                setCalendarStatus("connected");
                setMessage(null);
            } else if (data.status === "started" || data.status === "in_progress") {
                setMessage(data.message || "Complete authorization in the browser window...");

                pollTimeoutRef.current = setTimeout(() => {
                    if (calendarStatus === "loading") {
                        setCalendarStatus("timeout");
                        setCalendarError({
                            title: "Authorization Timeout",
                            message: "The authorization window may have been closed or blocked.",
                            suggestion: "Try again and complete the Google login process."
                        });
                        setMessage(null);
                    }
                }, 120000);
            } else {
                throw new Error("Unexpected response from server");
            }
        } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Unknown error";
            setCalendarError({
                title: "Connection Failed",
                message: errorMessage,
                suggestion: "Check the browser console and backend logs for details."
            });
            setCalendarStatus("error");
            setMessage(null);
        }
    };

    const handleCalendarTest = async () => {
        setMessage("Đang kiểm tra Calendar...");
        try {
            const resp = await fetch("http://localhost:8000/api/calendar/events/upcoming?days=3&max_results=5");
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${resp.status}`);
            }
            const data = await resp.json();
            setMessage(data.result || "Calendar ok");
        } catch (e) {
            const msg = e instanceof Error ? e.message : "Unknown error";
            setCalendarError({
                title: "Calendar test failed",
                message: msg,
                suggestion: "Đảm bảo đã connect và token còn hạn."
            });
            setCalendarStatus("error");
        }
    };

    const handleGmailDisconnect = async () => {
        try {
            await fetch("http://localhost:8000/api/auth/gmail/disconnect", { method: "POST" });
            setGmailStatus("idle");
            setGmailError(null);
            setMessage(null);
        } catch (e) {
            console.error("Failed to disconnect Gmail:", e);
        }
    };

    const handleCalendarDisconnect = async () => {
        try {
            await fetch("http://localhost:8000/api/auth/calendar/disconnect", { method: "POST" });
            setCalendarStatus("idle");
            setCalendarError(null);
            setMessage(null);
        } catch (e) {
            console.error("Failed to disconnect Calendar:", e);
        }
    };

    const resetGmailError = () => {
        setGmailStatus("idle");
        setGmailError(null);
    };

    const resetCalendarError = () => {
        setCalendarStatus("idle");
        setCalendarError(null);
    };

    if (!isOpen) return null;

    // Error Card Component
    const ErrorCard = ({
        error,
        onRetry,
        onDismiss,
        serviceName
    }: {
        error: ErrorDetails;
        onRetry: () => void;
        onDismiss: () => void;
        serviceName: string;
    }) => (
        <div className="p-4 rounded-xl bg-gradient-to-br from-red-500/10 to-red-600/5 border border-red-500/30 space-y-3">
            {/* Error Header */}
            <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
                    <XCircle className="w-5 h-5 text-red-400" />
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-semibold text-red-400">{error.title}</h4>
                    <p className="text-xs text-red-300/80 mt-0.5">{serviceName} authorization unsuccessful</p>
                </div>
            </div>

            {/* Error Details */}
            <div className="pl-[52px] space-y-2">
                <p className="text-sm text-[var(--text-muted)]">{error.message}</p>
                <p className="text-xs text-[var(--text-dim)] flex items-start gap-1.5">
                    <Lightbulb className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0 mt-0.5" />
                    <span>{error.suggestion}</span>
                </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pl-[52px]">
                <button
                    onClick={onRetry}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/30 transition-colors cursor-pointer"
                >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Try Again
                </button>
                <button
                    onClick={onDismiss}
                    className="px-3 py-1.5 rounded-lg text-[var(--text-muted)] text-sm hover:bg-[var(--surface-hover)] transition-colors cursor-pointer"
                >
                    Dismiss
                </button>
            </div>
        </div>
    );

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center backdrop" onClick={onClose}>
            <div
                className="w-full max-w-md mx-4 surface rounded-xl shadow-2xl animate-fade-in max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] sticky top-0 surface z-10">
                    <h2 className="text-lg font-semibold text-[var(--text)]">Connections</h2>
                    <button
                        onClick={onClose}
                        className="p-1 rounded-lg hover:bg-[var(--surface-hover)] transition-colors cursor-pointer"
                    >
                        <X className="w-5 h-5 text-[var(--text-muted)]" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Info message */}
                    {message && (
                        <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
                            <ExternalLink className="w-4 h-4 text-blue-400 flex-shrink-0" />
                            <span className="text-sm text-blue-400">{message}</span>
                        </div>
                    )}

                    {/* Gmail Section */}
                    <div>
                            <button
                                onClick={handleCalendarTest}
                                className="px-3 py-2 rounded-lg border border-[var(--border)] text-sm text-[var(--text)] hover:bg-[var(--surface-hover)] transition-all cursor-pointer"
                            >
                                Test Calendar
                            </button>
                        <div className="flex items-center gap-2 mb-3">
                            <Mail className="w-4 h-4 text-[var(--text-muted)]" />
                            <span className="text-sm font-medium text-[var(--text)]">Gmail</span>
                        </div>

                        {/* Gmail Error State */}
                        {(gmailStatus === "error" || gmailStatus === "timeout") && gmailError ? (
                            <ErrorCard
                                error={gmailError}
                                onRetry={handleGmailConnect}
                                onDismiss={resetGmailError}
                                serviceName="Gmail"
                            />
                        ) : (
                            <>
                                <div className={`p-3 rounded-lg border mb-3 ${gmailStatus === "connected"
                                        ? "bg-green-500/10 border-green-500/30"
                                        : "bg-[var(--background)] border-[var(--border)]"
                                    }`}>
                                    <div className="flex items-center gap-2">
                                        {gmailStatus === "connected" && <Check className="w-4 h-4 text-green-400" />}
                                        {gmailStatus === "loading" && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                                        <p className={`text-sm ${gmailStatus === "connected" ? "text-green-400" : "text-[var(--text-muted)]"}`}>
                                            {gmailStatus === "connected"
                                                ? "Gmail connected successfully!"
                                                : gmailStatus === "loading"
                                                    ? "Waiting for authorization..."
                                                    : "Not connected - Click below to authorize"}
                                        </p>
                                    </div>
                                </div>

                                {gmailStatus === "connected" ? (
                                    <button
                                        onClick={handleGmailDisconnect}
                                        className="w-full py-2.5 px-4 rounded-lg border border-red-500/30 text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                                    >
                                        Disconnect Gmail
                                    </button>
                                ) : (
                                    <button
                                        onClick={handleGmailConnect}
                                        disabled={gmailStatus === "loading"}
                                        className="w-full py-2.5 px-4 rounded-lg border border-[var(--border)] text-sm font-medium hover:bg-[var(--surface-hover)] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                    >
                                        {gmailStatus === "loading" ? (
                                            <>
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                Waiting for Google...
                                            </>
                                        ) : (
                                            "+ Connect Gmail"
                                        )}
                                    </button>
                                )}
                            </>
                        )}
                    </div>

                    {/* Divider */}
                    <div className="border-t border-[var(--border)]" />

                    {/* Calendar Section */}
                    <div>
                        <div className="flex items-center gap-2 mb-3">
                            <Calendar className="w-4 h-4 text-[var(--text-muted)]" />
                            <span className="text-sm font-medium text-[var(--text)]">Google Calendar</span>
                        </div>

                        {/* Calendar Error State */}
                        {(calendarStatus === "error" || calendarStatus === "timeout") && calendarError ? (
                            <ErrorCard
                                error={calendarError}
                                onRetry={handleCalendarConnect}
                                onDismiss={resetCalendarError}
                                serviceName="Calendar"
                            />
                        ) : (
                            <div className={`flex items-center justify-between p-3 rounded-lg border ${calendarStatus === "connected"
                                    ? "bg-green-500/10 border-green-500/30"
                                    : "bg-[var(--background)] border-[var(--border)]"
                                }`}>
                                <div className="flex items-center gap-3">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${calendarStatus === "connected"
                                            ? "bg-green-500/20"
                                            : "bg-[var(--accent)]/20"
                                        }`}>
                                        {calendarStatus === "loading" ? (
                                            <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                                        ) : calendarStatus === "connected" ? (
                                            <Check className="w-4 h-4 text-green-400" />
                                        ) : (
                                            <Calendar className="w-4 h-4 text-[var(--accent)]" />
                                        )}
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-[var(--text)]">Google Calendar</p>
                                        <p className={`text-xs ${calendarStatus === "connected" ? "text-green-400" : "text-[var(--text-muted)]"}`}>
                                            {calendarStatus === "connected"
                                                ? "Connected"
                                                : calendarStatus === "loading"
                                                    ? "Connecting..."
                                                    : "Not connected"}
                                        </p>
                                    </div>
                                </div>

                                {calendarStatus === "connected" ? (
                                    <button
                                        onClick={handleCalendarDisconnect}
                                        className="px-4 py-1.5 rounded-lg text-sm font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors cursor-pointer"
                                    >
                                        Disconnect
                                    </button>
                                ) : (
                                    <button
                                        onClick={handleCalendarConnect}
                                        disabled={calendarStatus === "loading"}
                                        className="px-4 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer bg-[var(--accent)] text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {calendarStatus === "loading" ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            "Connect"
                                        )}
                                    </button>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Help text */}
                    <p className="text-xs text-[var(--text-dim)] flex items-center gap-1.5">
                        <Lightbulb className="w-3.5 h-3.5 text-yellow-500" />
                        A Google login window will open automatically. Grant access to connect.
                    </p>
                </div>
            </div>
        </div>
    );
}
