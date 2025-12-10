"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  ArrowUp,
  Loader2,
  ChevronDown,
  ChevronRight,
  Wrench,
  ClipboardList,
  Mail,
  Brain,
  Newspaper,
  MessageCircle,
  Paperclip,
  FileText,
  X,
  GraduationCap,
  Bug,
} from "lucide-react";
import { Message } from "./Message";
import { QuizMessage } from "../QuizMessage";
import { useAppStore } from "@/store/useAppStore";

interface QuizData {
  title: string;
  difficulty: string;
  questions: Array<{
    type?: string;
    question: string;
    options: string[];
    correct_answer: string;
    explanation: string;
  }>;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tools?: string[];
  thinking?: string;
  debugInfo?: string;
  quizData?: QuizData;
}

const SUGGESTIONS = [
  {
    label: "Tasks của tôi",
    prompt: "What are my pending tasks and todos?",
    icon: ClipboardList,
  },
  {
    label: "Email mới nhất",
    prompt: "Check my last email and summarize it.",
    icon: Mail,
  },
  {
    label: "Tạo quiz",
    prompt: "Create a quiz about Python programming.",
    icon: Brain,
  },
  {
    label: "Tin tech",
    prompt: "What are the latest tech news headlines?",
    icon: Newspaper,
  },
];

interface AttachedDocument {
  id: string;
  filename: string;
  page_count: number;
}

interface ChatContainerProps {
  sessionId?: string | null;
  onMessagesChange?: (messages: ChatMessage[]) => void;
  onSessionCreated?: (sessionId: string) => void;
  onDocumentAttached?: (doc: AttachedDocument) => void;
  attachedDocId?: string;
  greeting?: string;
}

const API_BASE = "http://localhost:8000/api";

interface StudyToggleButtonProps {
  mode: "emo_only" | "study" | null;
  onClick: () => void;
}

function StudyToggleButton({ mode, onClick }: StudyToggleButtonProps) {
  const isEmoOnly = mode === "emo_only";
  const isStudy = mode === "study";
  return (
    <button
      onClick={onClick}
      className={`group flex items-center gap-2 px-4 h-10 rounded-full text-sm font-medium cursor-pointer select-none ${
        isEmoOnly
          ? "bg-yellow-100 text-yellow-700"
          : isStudy
          ? "bg-blue-100 text-blue-700"
          : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
      }`}
    >
      <GraduationCap
        className={`w-4 h-4 ${
          isEmoOnly
            ? "text-yellow-700"
            : isStudy
            ? "text-blue-700"
            : "text-gray-500 group-hover:text-gray-700"
        }`}
        strokeWidth={2}
      />
      Study
    </button>
  );
}

export function ChatContainer({
  sessionId,
  onMessagesChange,
  onSessionCreated,
  onDocumentAttached,
  attachedDocId,
  greeting = "Good morning, Josh!",
}: ChatContainerProps = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedThinking, setExpandedThinking] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const { debugMode, chatMode, setChatMode } = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const onMessagesChangeRef = useRef(onMessagesChange);

  // Keep the callback stable to avoid re-trigger loops
  useEffect(() => {
    onMessagesChangeRef.current = onMessagesChange;
  }, [onMessagesChange]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const cycleChatMode = () => {
    const current = chatMode;
    if (current === null) setChatMode("emo_only");
    else if (current === "emo_only") setChatMode("study");
    else setChatMode(null);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load messages when sessionId changes
  useEffect(() => {
    if (sessionId) {
      loadSessionMessages(sessionId);
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  // Handle quiz generation
  const generateQuiz = useCallback(
    async (
      docId: string,
      page: number,
      difficulty: string,
      selectedText?: string
    ) => {
      // Add user message
      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        role: "user",
        content: selectedText
          ? `📝 Tạo quiz từ đoạn văn đã chọn (độ khó: ${
              difficulty === "Beginner"
                ? "Dễ"
                : difficulty === "Intermediate"
                ? "Trung bình"
                : "Khó"
            })`
          : `📝 Tạo quiz từ trang ${page} (độ khó: ${
              difficulty === "Beginner"
                ? "Dễ"
                : difficulty === "Intermediate"
                ? "Trung bình"
                : "Khó"
            })`,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const res = await fetch(`${API_BASE}/documents/quiz`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            doc_id: docId,
            page: selectedText ? undefined : page,
            context: selectedText || undefined,
            difficulty,
            num_questions: 5,
          }),
        });

        if (!res.ok) throw new Error("Quiz generation failed");
        const data = await res.json();

        // Add quiz message
        const quizMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "",
          quizData: {
            title: data.title,
            difficulty: data.difficulty,
            questions: data.questions,
          },
        };
        setMessages((prev) => [...prev, quizMsg]);
      } catch (error) {
        console.error("Quiz error:", error);
        const errMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "❌ Không thể tạo quiz. Vui lòng thử lại.",
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // Listen for quiz requests from DocumentPanel
  useEffect(() => {
    const handleQuizRequest = (event: CustomEvent) => {
      const { docId, page, difficulty, selectedText, isPageQuiz } =
        event.detail;
      if (docId) {
        generateQuiz(
          docId,
          page,
          difficulty,
          isPageQuiz ? undefined : selectedText
        );
      }
    };

    window.addEventListener("quizRequest", handleQuizRequest as EventListener);
    return () =>
      window.removeEventListener(
        "quizRequest",
        handleQuizRequest as EventListener
      );
  }, [generateQuiz]);

  const loadSessionMessages = async (sid: string) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/chat/sessions/${sid}`
      );
      if (response.ok) {
        const data = await response.json();
        const loadedMessages: ChatMessage[] = data.messages.map((msg: any) => ({
          id: msg.timestamp,
          role: msg.role,
          content: msg.content,
        }));
        setMessages(loadedMessages);
      }
    } catch (error) {
      console.error("Failed to load session messages:", error);
    }
  };

  // Notify parent of message changes without re-render loop
  useEffect(() => {
    if (onMessagesChangeRef.current) {
      onMessagesChangeRef.current(messages);
    }
  }, [messages]);

  const sendMessage = async (messageText: string) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: messageText.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Smart routing: Detect email queries and use direct API
      const isEmailQuery = /^(check email|đọc mail|xem mail|email|mail)/i.test(
        messageText.trim()
      );

      if (isEmailQuery) {
        // Direct API call for email list (10x faster!)
        const response = await fetch("http://localhost:8000/api/emails/list");

        if (response.ok) {
          const data = await response.json();

          const assistantMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: data.content,
          };

          setMessages((prev) => [...prev, assistantMessage]);
          setIsLoading(false);
          return; // Exit early, don't call AI
        }
        // If direct API fails, fall through to AI method
      }

      // Default: Use AI for all other queries with STREAMING
      // Build context from previous messages
      const previousMessages = messages
        .map((m) => `${m.role === "user" ? "User" : "Emo"}: ${m.content}`)
        .join("\n");

      // Prepare message data (but don't add to state yet)
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        tools: [],
        thinking: "",
      };
      // Don't add message yet - wait for first token

      // Use streaming endpoint with Server-Sent Events
      const encodedMessage = encodeURIComponent(userMessage.content);
      const sessionParam = sessionId ? `&session_id=${sessionId}` : "";
      const modeParam = chatMode ? `&mode=${chatMode}` : "";
      const debugParam = debugMode ? "&debug=true" : "";
      const eventSource = new EventSource(
        `http://localhost:8000/api/chat/stream?message=${encodedMessage}${sessionParam}${modeParam}${debugParam}`
      );

      let accumulatedContent = "";
      let accumulatedTools: string[] = [];
      let accumulatedThinking = "";
      let accumulatedDebugInfo = "";
      let messageCreated = false; // Track if message was added to state
      let newSessionId: string | null = null; // Track auto-created session

      eventSource.onmessage = (event) => {
        if (event.data === "[DONE]") {
          eventSource.close();
          setIsLoading(false);

          // If session was auto-created, navigate to the new session URL
          if (newSessionId && onSessionCreated) {
            onSessionCreated(newSessionId);
          }
          return;
        }

        try {
          const chunk = JSON.parse(event.data);

          // Handle session_id from backend
          if (chunk.type === "session_id" && chunk.session_id) {
            // Only save for navigation if we didn't start with a session
            if (!sessionId) {
              newSessionId = chunk.session_id;
            }
            // Don't navigate yet - wait for stream to complete
            return;
          }

          if (chunk.error) {
            eventSource.close();
            // Create message with error if not created yet
            if (!messageCreated) {
              setMessages((prev) => [
                ...prev,
                { ...assistantMessage, content: `Lỗi: ${chunk.error}` },
              ]);
            } else {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: `Lỗi: ${chunk.error}` }
                    : msg
                )
              );
            }
            setIsLoading(false);
            return;
          }

          // Accumulate content based on chunk type
          if (chunk.type === "text" && chunk.content) {
            accumulatedContent += chunk.content;
          }
          if (chunk.type === "tool" && chunk.name) {
            accumulatedTools.push(chunk.name);
          }
          if (chunk.type === "done" && chunk.full_response) {
            accumulatedContent = chunk.full_response;
          }
          if (chunk.tools_used) {
            accumulatedTools = chunk.tools_used;
          }
          if (chunk.thinking) {
            accumulatedThinking = chunk.thinking;
          }
          if (chunk.debug_info) {
            accumulatedDebugInfo = chunk.debug_info;
          }

          // Create message on first chunk, then update it
          if (!messageCreated && accumulatedContent) {
            messageCreated = true;
            setMessages((prev) => [
              ...prev,
              {
                ...assistantMessage,
                content: accumulatedContent,
                tools: accumulatedTools,
                thinking: accumulatedThinking,
                debugInfo: accumulatedDebugInfo,
              },
            ]);
          } else if (messageCreated) {
            // Update existing message
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      content: accumulatedContent,
                      tools: accumulatedTools,
                      thinking: accumulatedThinking,
                      debugInfo: accumulatedDebugInfo,
                    }
                  : msg
              )
            );
          }
        } catch (parseError) {
          console.error("Error parsing SSE chunk:", parseError);
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE Error:", error);
        eventSource.close();

        // Show error message
        if (!messageCreated) {
          // Create message with error if not created yet
          setMessages((prev) => [
            ...prev,
            {
              ...assistantMessage,
              content: "Không thể kết nối đến server. Vui lòng thử lại.",
            },
          ]);
        } else if (!accumulatedContent) {
          // Update existing message with error
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: "Không thể kết nối đến server. Vui lòng thử lại.",
                  }
                : msg
            )
          );
        }
        setIsLoading(false);
      };
    } catch (outerError) {
      console.error("Error:", outerError);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Có lỗi xảy ra. Vui lòng thử lại.",
      };
      setMessages((prev) => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendMessage(input);
  };

  const handleSuggestionClick = (prompt: string) => {
    sendMessage(prompt);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const toggleThinking = (messageId: string) => {
    setExpandedThinking(expandedThinking === messageId ? null : messageId);
  };

  const handleDirectEmailFetch = (content: string) => {
    // Add email content as assistant message immediately
    const emailMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "assistant",
      content: content,
    };
    setMessages((prev) => [...prev, emailMessage]);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = [".pdf", ".txt", ".docx", ".doc"];
    const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
    if (!validTypes.includes(fileExt)) {
      const errorMsg: ChatMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: "⚠️ Chỉ hỗ trợ file PDF, TXT, hoặc Word (.docx).",
      };
      setMessages((prev) => [...prev, errorMsg]);
      return;
    }

    setIsUploading(true);

    try {
      // If no session exists, create one first
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        const createRes = await fetch(`${API_BASE}/chat/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: `📄 ${file.name}` }),
        });

        if (createRes.ok) {
          const newSession = await createRes.json();
          currentSessionId = newSession.id;
          if (onSessionCreated && currentSessionId) {
            onSessionCreated(currentSessionId);
          }
        }
      }

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Upload failed");
      }

      const doc = await res.json();

      // Notify parent component
      if (onDocumentAttached) {
        onDocumentAttached({
          id: doc.id,
          filename: doc.filename,
          page_count: doc.page_count,
        });
      }

      // Add success message
      const successMsg: ChatMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: `📄 **${doc.filename}** đã được tải lên (${doc.page_count} trang). Bạn có thể hỏi về nội dung hoặc tạo quiz từ tài liệu này.`,
      };
      setMessages((prev) => [...prev, successMsg]);
    } catch (error) {
      const errorMsg: ChatMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: "❌ Không thể tải file lên. Vui lòng thử lại.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-8 max-w-3xl mx-auto w-full">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4">
            {/* Bold greeting - centered */}
            <h1 className="text-4xl font-bold mb-8 text-[var(--text)] leading-tight text-left">
              {greeting}
            </h1>

            {/* Claude-style input card */}
            <div className="w-full max-w-2xl bg-white rounded-2xl p-3 border border-[var(--border)] mb-6 transition-all focus-within:ring-1 focus-within:ring-[var(--primary-light)]">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height =
                    Math.min(e.target.scrollHeight, 120) + "px";
                }}
                onKeyDown={handleKeyDown}
                placeholder="Nhắn Emo..."
                rows={1}
                className="input-borderless w-full bg-transparent resize-none text-base placeholder:text-[var(--text-dim)] text-[var(--text)]"
                style={{ minHeight: "24px", maxHeight: "120px" }}
                disabled={isLoading}
              />
              <div className="flex items-center justify-between mt-2 pt-2">
                <div className="flex items-center gap-2">
                  <StudyToggleButton mode={chatMode} onClick={cycleChatMode} />
                  {/* File attachment button */}
                  <label className="p-2 rounded-lg hover:bg-[var(--surface-hover)] cursor-pointer transition-colors group">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.txt,.docx,.doc"
                      onChange={handleFileUpload}
                      className="hidden"
                      disabled={isUploading}
                    />
                    {isUploading ? (
                      <Loader2 className="w-5 h-5 text-[var(--text-dim)] animate-spin" />
                    ) : (
                      <Paperclip className="w-5 h-5 text-[var(--text-dim)] group-hover:text-[var(--text-muted)]" />
                    )}
                  </label>
                </div>
                <button
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || isLoading}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all"
                  aria-label="Send message"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowUp className="w-5 h-5" strokeWidth={2.5} />
                  )}
                </button>
              </div>
            </div>

            {/* Suggestion chips */}
            <div className="flex flex-wrap gap-3 justify-center max-w-2xl">
              {SUGGESTIONS.map((suggestion) => {
                const IconComponent = suggestion.icon;
                return (
                  <button
                    key={suggestion.label}
                    onClick={() => handleSuggestionClick(suggestion.prompt)}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-[var(--surface)] border border-[var(--border)] text-[var(--text-muted)] text-sm hover:bg-[var(--surface-hover)] hover:border-[var(--border-light)] hover:text-[var(--text)] transition-all cursor-pointer"
                  >
                    <IconComponent className="w-4 h-4" />
                    <span>{suggestion.label}</span>
                  </button>
                );
              })}
            </div>

            <p className="text-center text-xs text-[var(--text-dim)] mt-10">
              EMO có thể mắc lỗi. Kiểm tra thông tin quan trọng.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((message) => (
              <div key={message.id}>
                {/* Quiz Message */}
                {message.quizData ? (
                  <div className="animate-fade-in">
                    {message.role === "user" && (
                      <Message
                        message={message}
                        onViewEmail={(viewMessage) => sendMessage(viewMessage)}
                        onDirectEmailFetch={handleDirectEmailFetch}
                      />
                    )}
                    {message.role === "assistant" && (
                      <div className="ml-0 md:ml-12 mt-2">
                        <QuizMessage
                          title={message.quizData.title}
                          difficulty={message.quizData.difficulty}
                          questions={message.quizData.questions}
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  /* Regular Message */
                  <Message
                    message={message}
                    onViewEmail={(viewMessage) => sendMessage(viewMessage)}
                    onDirectEmailFetch={handleDirectEmailFetch}
                  />
                )}

                {/* Thinking Process Expander */}
                {message.role === "assistant" &&
                  message.thinking &&
                  !message.quizData && (
                    <div className="ml-12 mt-2">
                      <button
                        onClick={() => toggleThinking(message.id)}
                        className="flex items-center gap-1 text-xs text-[var(--text-dim)] hover:text-[var(--text-muted)] transition-colors cursor-pointer"
                      >
                        {expandedThinking === message.id ? (
                          <ChevronDown className="w-3 h-3" />
                        ) : (
                          <ChevronRight className="w-3 h-3" />
                        )}
                        <MessageCircle className="w-3 h-3" />
                        Thinking process
                      </button>

                      {expandedThinking === message.id && (
                        <div className="mt-2 p-3 rounded-xl bg-[var(--background)] border border-[var(--border)] text-xs text-[var(--text-muted)] animate-fade-in">
                          <div className="flex items-center gap-2 mb-2">
                            <Wrench className="w-3 h-3" />
                            <span className="font-medium">Tool calls:</span>
                          </div>
                          <pre className="whitespace-pre-wrap font-mono">
                            {message.thinking}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                {/* Debug Info Panel */}
                {debugMode &&
                  message.role === "assistant" &&
                  message.debugInfo && (
                    <div className="mt-3 p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs animate-fade-in">
                      <div className="flex items-center gap-2 mb-2 text-amber-700">
                        <Bug className="w-4 h-4" />
                        <span className="font-semibold">Debug Info</span>
                      </div>
                      <pre className="whitespace-pre-wrap font-mono text-amber-900 max-h-96 overflow-y-auto">
                        {message.debugInfo}
                      </pre>
                    </div>
                  )}
              </div>
            ))}

            {isLoading &&
              (messages.length === 0 ||
                messages[messages.length - 1]?.role === "user") && (
                <div className="animate-fade-in py-2">
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[var(--text-dim)] animate-pulse" />
                    <span
                      className="w-2 h-2 rounded-full bg-[var(--text-dim)] animate-pulse"
                      style={{ animationDelay: "0.2s" }}
                    />
                    <span
                      className="w-2 h-2 rounded-full bg-[var(--text-dim)] animate-pulse"
                      style={{ animationDelay: "0.4s" }}
                    />
                  </div>
                </div>
              )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area - same card style as home page */}
      {messages.length > 0 && (
        <div className="px-4 pb-6 pt-4 max-w-3xl mx-auto w-full">
          <div className="w-full bg-white rounded-2xl p-3 border border-[var(--border)] transition-all focus-within:ring-1 focus-within:ring-[var(--primary-light)]">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height =
                  Math.min(e.target.scrollHeight, 120) + "px";
              }}
              onKeyDown={handleKeyDown}
              placeholder="Nhắn Emo..."
              rows={1}
              className="input-borderless w-full bg-transparent resize-none text-base placeholder:text-[var(--text-dim)] text-[var(--text)]"
              style={{ minHeight: "24px", maxHeight: "120px" }}
              disabled={isLoading}
            />
            <div className="flex items-center justify-between mt-2 pt-2">
              <div className="flex items-center gap-2">
                <StudyToggleButton mode={chatMode} onClick={cycleChatMode} />
                {/* File attachment button */}
                <label className="p-2 rounded-lg hover:bg-[var(--surface-hover)] cursor-pointer transition-colors group">
                  <input
                    type="file"
                    accept=".pdf,.txt,.docx,.doc"
                    onChange={handleFileUpload}
                    className="hidden"
                    disabled={isUploading}
                  />
                  {isUploading ? (
                    <Loader2 className="w-5 h-5 text-[var(--text-dim)] animate-spin" />
                  ) : (
                    <Paperclip className="w-5 h-5 text-[var(--text-dim)] group-hover:text-[var(--text-muted)]" />
                  )}
                </label>
              </div>
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isLoading}
                className="w-10 h-10 flex items-center justify-center rounded-full bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-all"
                aria-label="Send message"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowUp className="w-5 h-5" strokeWidth={2.5} />
                )}
              </button>
            </div>
          </div>
          <p className="text-center text-[10px] text-[var(--text-dim)] mt-3">
            EMO có thể mắc lỗi. Kiểm tra thông tin quan trọng.
          </p>
        </div>
      )}
    </div>
  );
}
