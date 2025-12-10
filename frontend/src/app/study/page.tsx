"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, Loader2, BookOpen, ArrowRight } from "lucide-react";

const API_BASE = "http://localhost:8000/api";

interface Document {
  id: string;
  filename: string;
  page_count: number;
  uploaded_at: string;
}

export default function StudyHome() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Failed to fetch documents");
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Chỉ hỗ trợ file PDF");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const doc = await res.json();
      setDocuments((prev) => [doc, ...prev]);

      // Navigate to study page
      await router.push(`/study/${doc.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload thất bại");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--text)] p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4 flex items-center justify-center gap-3">
            <BookOpen className="w-10 h-10 text-[var(--primary)]" />
            SocratiQ
          </h1>
          <p className="text-[var(--text-muted)] text-lg">
            Upload PDF để học với AI Quiz Generator
          </p>
        </div>

        {/* Upload Zone */}
        <label className="block mb-8">
          <div className="border-2 border-dashed border-[var(--border)] rounded-2xl p-12 text-center cursor-pointer hover:border-[var(--primary)] hover:bg-[var(--surface)] transition-all duration-200">
            {uploading ? (
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-12 h-12 text-[var(--primary)] animate-spin" />
                <p className="text-[var(--text-muted)]">Đang xử lý PDF...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4">
                <Upload className="w-12 h-12 text-[var(--text-dim)]" />
                <div>
                  <p className="text-lg font-medium">
                    Kéo thả hoặc click để upload PDF
                  </p>
                  <p className="text-sm text-[var(--text-dim)] mt-1">
                    Hỗ trợ file PDF
                  </p>
                </div>
              </div>
            )}
          </div>
          <input
            type="file"
            accept=".pdf"
            onChange={handleUpload}
            ref={fileInputRef}
            className="hidden"
            disabled={uploading}
          />
        </label>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-center">
            {error}
          </div>
        )}

        {/* Documents List */}
        {documents.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Tài liệu của bạn</h2>
            <div className="space-y-3">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => router.push(`/study/${doc.id}`)}
                  className="w-full flex items-center justify-between p-4 bg-[var(--surface)] border border-[var(--border)] rounded-xl hover:bg-[var(--surface-hover)] hover:border-[var(--primary)] transition-all group cursor-pointer"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-[var(--primary)]/10 rounded-lg">
                      <FileText className="w-6 h-6 text-[var(--primary)]" />
                    </div>
                    <div className="text-left">
                      <p className="font-medium">{doc.filename}</p>
                      <p className="text-sm text-[var(--text-dim)]">
                        {doc.page_count} trang
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-[var(--text-dim)] group-hover:text-[var(--primary)] group-hover:translate-x-1 transition-all" />
                </button>
              ))}
            </div>
          </div>
        )}

        {documents.length === 0 && !loading && (
          <div className="text-center py-12 text-[var(--text-dim)]">
            <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p>Chưa có tài liệu nào. Upload PDF để bắt đầu!</p>
          </div>
        )}
      </div>
    </div>
  );
}
