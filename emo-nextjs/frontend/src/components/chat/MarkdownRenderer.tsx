"use client";

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface MarkdownRendererProps {
    content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
    return (
        <div className="markdown-content">
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    // Style paragraphs
                    p: ({ children }) => (
                        <p className="mb-1 last:mb-0">{children}</p>
                    ),
                    // Style bold text
                    strong: ({ children }) => (
                        <strong className="font-bold text-[var(--text)]">{children}</strong>
                    ),
                    // Style strikethrough
                    del: ({ children }) => (
                        <del className="line-through opacity-70">{children}</del>
                    ),
                    // Style todo lists
                    input: ({ checked, ...props }) => (
                        <input
                            type="checkbox"
                            checked={checked}
                            disabled
                            className="mr-2 align-middle cursor-default"
                            {...props}
                        />
                    ),
                    // Style list items
                    li: ({ children, className }) => {
                        const isTaskItem = className?.includes('task-list-item');
                        return (
                            <li className={`${isTaskItem ? 'list-none' : 'ml-4'} mb-1`}>
                                {children}
                            </li>
                        );
                    },
                    // Style unordered lists
                    ul: ({ children, className }) => {
                        const isTaskList = className?.includes('contains-task-list');
                        return (
                            <ul className={`${isTaskList ? 'space-y-1' : 'list-disc ml-4 space-y-1'} my-2`}>
                                {children}
                            </ul>
                        );
                    },
                    // Style ordered lists
                    ol: ({ children }) => (
                        <ol className="list-decimal ml-4 space-y-1 my-2">{children}</ol>
                    ),
                    // Style code blocks
                    code: ({ inline, className, children, ...props }: any) => {
                        if (inline) {
                            return (
                                <code
                                    className="bg-[var(--surface)] px-1.5 py-0.5 rounded text-sm font-mono border border-[var(--border)]"
                                    {...props}
                                >
                                    {children}
                                </code>
                            );
                        }
                        return (
                            <code
                                className={`block bg-[var(--surface)] p-3 rounded-lg my-2 overflow-x-auto font-mono text-sm border border-[var(--border)] ${className || ''}`}
                                {...props}
                            >
                                {children}
                            </code>
                        );
                    },
                    // Style pre blocks
                    pre: ({ children }) => (
                        <pre className="my-2">{children}</pre>
                    ),
                    // Style headings
                    h1: ({ children }) => (
                        <h1 className="text-xl font-bold mt-4 mb-2">{children}</h1>
                    ),
                    h2: ({ children }) => (
                        <h2 className="text-lg font-bold mt-3 mb-2">{children}</h2>
                    ),
                    h3: ({ children }) => (
                        <h3 className="text-base font-bold mt-2 mb-1">{children}</h3>
                    ),
                    // Style blockquotes
                    blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-[var(--primary)] pl-4 my-2 italic opacity-80">
                            {children}
                        </blockquote>
                    ),
                    // Style links with URL truncation
                    a: ({ children, href }) => {
                        // Truncate long URLs in display
                        let displayText = children;

                        // Check if children is a string and looks like a URL
                        if (typeof children === 'string' && children.startsWith('http')) {
                            if (children.length > 50) {
                                displayText = children.substring(0, 47) + '...';
                            }
                        }

                        return (
                            <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[var(--primary)] hover:underline break-all"
                                title={typeof children === 'string' ? children : href}
                            >
                                {displayText}
                            </a>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
