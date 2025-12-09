"use client";

import { useState } from "react";
import { Mail, Paperclip, Eye, Loader2 } from "lucide-react";

interface EmailItem {
    index: number;
    sender: string;
    subject: string;
    date: string;
    hasAttachment?: boolean;
}

interface EmailCardProps {
    emails: EmailItem[];
    onViewEmail?: (message: string) => void;
    onDirectEmailFetch?: (content: string) => void;
}

// Simple hash for consistent avatar colors
const COLORS = ["purple", "blue", "cyan", "green", "orange", "pink"];
function getAvatarColor(sender: string): string {
    let hash = 0;
    for (let i = 0; i < sender.length; i++) {
        hash = sender.charCodeAt(i) + ((hash << 5) - hash);
    }
    return COLORS[Math.abs(hash) % COLORS.length];
}

// Get initials from sender name
function getInitials(sender: string): string {
    if (!sender || sender.trim().length === 0) {
        return "??";
    }

    const cleaned = sender.replace(/<[^>]*>/g, "").trim();

    if (cleaned.length === 0) {
        return "??";
    }

    const words = cleaned.split(/\s+/).filter(w => w.length > 0);

    if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase();
    }

    if (cleaned.length === 1) {
        return cleaned.toUpperCase() + cleaned.toUpperCase();
    }

    return cleaned.substring(0, 2).toUpperCase();
}

// Parse email list from AI response
export function parseEmailList(content: string): EmailItem[] {
    const lines = content.split("\n");
    const emails: EmailItem[] = [];

    for (const line of lines) {
        // Match pattern: [1] then rest of line
        const indexMatch = line.match(/^\[(\d+)\]\s*(.+)$/);
        if (indexMatch) {
            const index = parseInt(indexMatch[1]);
            const rest = indexMatch[2];

            // Split by " - " (with spaces) to avoid breaking on dashes in subject
            const parts = rest.split(" - ");
            if (parts.length >= 3) {
                // Last part is date, first part is sender, middle is subject
                const sender = parts[0].trim() || "Unknown Sender";
                const date = parts[parts.length - 1].trim() || "Unknown Date";
                const subject = parts.slice(1, -1).join(" - ").trim() || "No Subject";

                emails.push({
                    index,
                    sender,
                    subject,
                    date,
                    hasAttachment: line.includes("Attachment"),
                });
            }
        }
    }

    return emails; // Always return array, never null
}

export function EmailCard({ emails, onViewEmail, onDirectEmailFetch }: EmailCardProps) {
    const [loadingIndex, setLoadingIndex] = useState<number | null>(null);

    const handleViewClick = async (email: EmailItem) => {
        setLoadingIndex(email.index);

        try {
            // Try direct API first (fast!)
            const response = await fetch(`http://localhost:8000/api/email/${email.index}`);

            if (response.ok) {
                const data = await response.json();
                if (onDirectEmailFetch) {
                    onDirectEmailFetch(data.content);
                }
            } else {
                // Fallback to AI method
                const message = `tôi muốn xem email "${email.subject}"`;
                if (onViewEmail) {
                    onViewEmail(message);
                }
            }
        } catch (error) {
            // Fallback to AI method on error
            const message = `tôi muốn xem email "${email.subject}"`;
            if (onViewEmail) {
                onViewEmail(message);
            }
        } finally {
            setTimeout(() => setLoadingIndex(null), 500);
        }
    };

    // Handle empty array
    if (!emails || emails.length === 0) {
        return null;
    }

    return (
        <div className="w-full max-w-lg">
            {/* Header */}
            <div className="flex items-center gap-2 mb-3 text-sm text-[var(--text-muted)]">
                <Mail className="w-4 h-4" />
                <span>{emails.length} email(s) found</span>
            </div>

            {/* Email list */}
            <div className="email-list">
                {emails.map((email) => {
                    const color = getAvatarColor(email.sender);
                    const initials = getInitials(email.sender);

                    return (
                        <div key={email.index} className="email-card group">
                            <div className="flex items-start gap-3">
                                {/* Index badge */}
                                <div className="email-index">{email.index}</div>

                                {/* Avatar */}
                                <div className={`email-avatar email-avatar--${color}`}>
                                    {initials}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    {/* Sender + Date row */}
                                    <div className="flex items-center justify-between gap-2 mb-1">
                                        <span className="font-medium text-sm text-[var(--text)] truncate">
                                            {email.sender}
                                        </span>
                                        <span className="email-date">{email.date}</span>
                                    </div>

                                    {/* Subject + Actions */}
                                    <div className="flex items-center gap-2">
                                        <p className="text-sm text-[var(--text-muted)] truncate flex-1">
                                            {email.subject}
                                        </p>
                                        {email.hasAttachment && (
                                            <Paperclip className="w-3 h-3 text-[var(--text-dim)] flex-shrink-0" />
                                        )}
                                        {/* View button with loading state */}
                                        <button
                                            onClick={() => handleViewClick(email)}
                                            disabled={loadingIndex === email.index}
                                            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] transition-all cursor-pointer flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                                            title="View full email"
                                        >
                                            {loadingIndex === email.index ? (
                                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            ) : (
                                                <Eye className="w-3.5 h-3.5" />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Hint - no emoji */}
            <p className="text-xs text-[var(--text-dim)] mt-3 text-center">
                Click the view button to read full email content
            </p>
        </div>
    );
}
