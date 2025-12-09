"use client";

import { Wrench } from "lucide-react";
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

    // Determine what to render
    const renderContent = () => {
        // User messages: cute bubble style
        if (isUser) {
            return (
                <div className="flex justify-end animate-fade-in">
                    <div className="max-w-[75%] px-4 py-2.5 rounded-2xl bg-[var(--surface-hover)] text-[var(--text)] text-base leading-relaxed">
                        {message.content.split("\n").map((line, i) => (
                            <p key={i} className="mb-0.5 last:mb-0">
                                {line || <br />}
                            </p>
                        ))}
                    </div>
                </div>
            );
        }

        // Assistant messages: plain text, no container (Copilot style)
        return (
            <div className="animate-fade-in">
                {/* Tool indicators */}
                {message.tools && message.tools.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2">
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

                {/* Check for email list format */}
                {emailList && emailList.length > 0 ? (
                    renderEmailList()
                ) : emailContentData ? (
                    renderEmailContent()
                ) : (
                    <div className="text-[var(--text)] text-base leading-relaxed">
                        <MarkdownRenderer content={message.content} />
                    </div>
                )}
            </div>
        );
    };

    return renderContent();
}

