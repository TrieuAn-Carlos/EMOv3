"use client";

import { Mail, Calendar, User, Paperclip, FileText } from "lucide-react";

interface EmailContentData {
    index: number;
    subject: string;
    sender: string;
    date: string;
    attachments?: string[];
    body: string;
}

interface EmailContentProps {
    email: EmailContentData;
}

// Parse email content from AI response
export function parseEmailContent(content: string): EmailContentData | null {
    // Check if it's an email format
    if (!content.includes("**Email #") && !content.includes("**Subject:**")) {
        return null;
    }

    const lines = content.split("\n");
    let index = 0;
    let subject = "";
    let sender = "";
    let date = "";
    let attachments: string[] = [];
    let bodyStartIndex = -1;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        // Parse Email #
        const indexMatch = line.match(/\*\*Email #(\d+)\*\*/);
        if (indexMatch) {
            index = parseInt(indexMatch[1]);
        }

        // Parse Subject
        const subjectMatch = line.match(/\*\*Subject:\*\*\s*(.+)/);
        if (subjectMatch) {
            subject = subjectMatch[1].trim();
        }

        // Parse From
        const fromMatch = line.match(/\*\*From:\*\*\s*(.+)/);
        if (fromMatch) {
            sender = fromMatch[1].trim();
        }

        // Parse Date
        const dateMatch = line.match(/\*\*Date:\*\*\s*(.+)/);
        if (dateMatch) {
            date = dateMatch[1].trim();
        }

        // Parse Attachments
        const attachMatch = line.match(/\*\*Attachments.*:\*\*\s*(.+)/);
        if (attachMatch) {
            attachments = attachMatch[1].split(",").map((a) => a.trim()).filter(a => a.length > 0);
        }

        // Find body start (after ---)
        if (line.includes("---") && bodyStartIndex === -1) {
            bodyStartIndex = i + 1;
        }
    }

    // Extract body
    const body = bodyStartIndex > 0 ? lines.slice(bodyStartIndex).join("\n").trim() : "";

    // Return with defaults if parsing failed
    return {
        index: index || 0,
        subject: subject || "No Subject",
        sender: sender || "Unknown Sender",
        date: date || "Unknown Date",
        attachments: attachments.length > 0 ? attachments : undefined,
        body: body || "(No content)"
    };
}

export function EmailContent({ email }: EmailContentProps) {
    // Get file icon based on extension
    const getFileIcon = (filename: string) => {
        if (filename.match(/\.(pdf)$/i)) return "📕";
        if (filename.match(/\.(doc|docx)$/i)) return "📄";
        if (filename.match(/\.(xls|xlsx)$/i)) return "📊";
        if (filename.match(/\.(ppt|pptx)$/i)) return "📊";
        if (filename.match(/\.(jpg|jpeg|png|gif)$/i)) return "🖼️";
        return "📎";
    };

    // Sanitize text to prevent XSS
    const sanitizeText = (text: string): string => {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    };

    return (
        <div className="email-content-card w-full max-w-2xl">
            {/* Header */}
            <div className="email-content-header">
                {/* Subject */}
                <h3 className="text-lg font-semibold text-[var(--text)] mb-3">
                    {email.subject}
                </h3>

                {/* Meta info */}
                <div className="flex flex-wrap items-center gap-4 text-sm">
                    {/* Sender */}
                    <div className="flex items-center gap-2 text-[var(--text-muted)]">
                        <User className="w-4 h-4" />
                        <span>{email.sender}</span>
                    </div>

                    {/* Date */}
                    <div className="flex items-center gap-2 text-[var(--text-dim)]">
                        <Calendar className="w-4 h-4" />
                        <span>{email.date}</span>
                    </div>
                </div>

                {/* Attachments */}
                {email.attachments && email.attachments.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                        {email.attachments.map((att, i) => (
                            <span key={i} className="attachment-badge">
                                <span>{getFileIcon(att)}</span>
                                <span className="truncate max-w-[150px]">{att}</span>
                            </span>
                        ))}
                    </div>
                )}
            </div>

            {/* Body - sanitized to prevent XSS */}
            <div className="email-content-body">
                {email.body.split("\n").map((line, i) => (
                    <p key={i} className="mb-2 last:mb-0">
                        {line ? (
                            <span dangerouslySetInnerHTML={{ __html: sanitizeText(line) }} />
                        ) : (
                            <br />
                        )}
                    </p>
                ))}
            </div>
        </div>
    );
}
