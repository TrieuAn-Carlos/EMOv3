"use client";

import { User, Sparkles, Wrench } from "lucide-react";
import { EmailCard, parseEmailList } from "./EmailCard";
import { EmailContent, parseEmailContent } from "./EmailContent";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface MessageProps {
    message: {
        id: string;
        role: "user" | "assistant";
        content: string;
        tools?: string[];
    };
    onViewEmail?: (message: string) => void;
    onDirectEmailFetch?: (content: string) => void;
}

export function Message({ message, onViewEmail, onDirectEmailFetch }: MessageProps) {
    const isUser = message.role === "user";

    // Try to parse as email list or email content
    const emailList = !isUser ? parseEmailList(message.content) : [];
    const emailContentData = !isUser ? parseEmailContent(message.content) : null;

    // Render email list card
    const renderEmailList = () => {
        if (!emailList || emailList.length === 0) return null;
        return <EmailCard emails={emailList} onViewEmail={onViewEmail} onDirectEmailFetch={onDirectEmailFetch} />;
    };

    // Render email content card
    const renderEmailContent = () => {
        if (!emailContentData) return null;
        return <EmailContent email={emailContentData} />;
    };

    // Render regular message
    const renderRegularMessage = () => {
        // For user messages, keep plain text rendering
        if (isUser) {
            return (
                <div
                    className="inline-block max-w-[85%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed bg-[var(--primary)] text-white shadow-sm"
                    style={{ borderBottomRightRadius: "6px" }}
                >
                    {message.content.split("\n").map((line, i) => (
                        <p key={i} className="mb-1 last:mb-0">
                            {line || <br />}
                        </p>
                    ))}
                </div>
            );
        }

        // For assistant messages, use markdown renderer
        return (
            <div
                className="inline-block max-w-[85%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] shadow-sm"
                style={{ borderBottomLeftRadius: "6px" }}
            >
                <MarkdownRenderer content={message.content} />
            </div>
        );
    };

    // Determine what to render for assistant messages
    const renderContent = () => {
        if (isUser) {
            return renderRegularMessage();
        }

        // Check for email list format
        if (emailList && emailList.length > 0) {
            return renderEmailList();
        }

        // Check for email content format
        if (emailContentData) {
            return renderEmailContent();
        }

        // Regular message
        return renderRegularMessage();
    };

    return (
        <div className={`flex gap-3.5 animate-fade-in ${isUser ? "flex-row-reverse" : "flex-row"}`}>
            {/* Avatar */}
            <div
                className={`flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center shadow-sm ${isUser
                    ? "bg-gradient-to-br from-[var(--primary)] to-[var(--primary-hover)] text-white"
                    : "bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] text-white shadow-glow"
                    }`}
            >
                {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
            </div>

            {/* Content */}
            <div className={`flex-1 min-w-0 ${isUser ? "text-right" : "text-left"}`}>
                {/* Tool indicators */}
                {message.tools && message.tools.length > 0 && (
                    <div className={`flex flex-wrap gap-1.5 mb-2.5 ${isUser ? "justify-end" : "justify-start"}`}>
                        {message.tools.map((tool, i) => (
                            <span
                                key={i}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] bg-[var(--surface)] border border-[var(--border)] text-[var(--text-muted)] font-medium"
                            >
                                <Wrench className="w-3 h-3" />
                                {tool}
                            </span>
                        ))}
                    </div>
                )}

                {/* Message content */}
                {renderContent()}
            </div>
        </div>
    );
}

