# 🎨 EMO Frontend UI Analysis

Tài liệu phân tích cấu trúc và thiết kế giao diện EMO để tái sử dụng context.

---

## 📁 Cấu trúc Files

```
frontend/src/
├── app/
│   ├── [[...sessionId]]/page.tsx   # Main page với dynamic routing
│   ├── globals.css                  # Theme system & component styles
│   ├── layout.tsx                   # Root layout
│   └── favicon.ico
│
├── components/
│   ├── chat/
│   │   ├── ChatContainer.tsx        # Container chính cho chat
│   │   ├── Message.tsx              # Render message bubbles
│   │   ├── EmailCard.tsx            # Card hiển thị danh sách email
│   │   ├── EmailContent.tsx         # Card hiển thị nội dung email
│   │   ├── MarkdownRenderer.tsx     # Render markdown response
│   │   └── index.ts                 # Export barrel
│   ├── ConnectionsDialog.tsx        # Modal quản lý Gmail/Calendar
│   └── SettingsDialog.tsx           # Modal settings (theme toggle)
│
└── store/
    ├── useAppStore.ts               # Global state (sessions, sidebar)
    └── useThemeStore.ts             # Theme state (light/dark/system)
```

---

## 🎯 Component Breakdown

### 1. `page.tsx` - Main Layout

**Đường dẫn:** `app/[[...sessionId]]/page.tsx`

**Cấu trúc:**

```
┌─────────────────────────────────────────────────┐
│  ┌────────┐  ┌─────────────────────────────────┐│
│  │SIDEBAR │  │         MAIN CONTENT            ││
│  │        │  │                                 ││
│  │ Panel  │  │       ChatContainer             ││
│  │ Toggle │  │                                 ││
│  │        │  │                                 ││
│  │ + New  │  │                                 ││
│  │        │  │                                 ││
│  │ Recents│  │                                 ││
│  │ - Chat1│  │                                 ││
│  │ - Chat2│  │                                 ││
│  │        │  │                                 ││
│  │────────│  │                                 ││
│  │Connect │  │                                 ││
│  │Settings│  │                                 ││
│  └────────┘  └─────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**Features:**

- Collapsible sidebar (64px collapsed, 256px expanded)
- Dynamic routing: `/` = new chat, `/[sessionId]` = existing session
- Session list với delete button on hover
- Bottom actions: Connections, Settings dialogs

**Key States (Zustand):**

- `isSidebarExpanded` - Boolean toggle sidebar
- `isRecentsExpanded` - Boolean toggle chat history section
- `sessions` - Array of chat sessions from backend

---

### 2. `ChatContainer.tsx` - Chat Logic

**Đường dẫn:** `components/chat/ChatContainer.tsx`

**Empty State (No Messages):**

```
┌─────────────────────────────────────────────────┐
│                                                 │
│          Good morning, Josh!                    │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  Nhắn Emo...                         🔼 │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  [Tasks] [Email] [Quiz] [Tin tech]              │
│                                                 │
│  EMO có thể mắc lỗi. Kiểm tra thông tin...      │
└─────────────────────────────────────────────────┘
```

**Has Messages State:**

```
┌─────────────────────────────────────────────────┐
│                                                 │
│                      [User bubble right-aligned]│
│  [Assistant text left-aligned, no bubble]       │
│                      [User bubble]              │
│  [Assistant with tool badges]                   │
│  ● ● ●  (loading dots if streaming)             │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  Nhắn Emo...                         🔼 │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

**Features:**

- **Streaming SSE:** Real-time character-by-character response
- **Smart Routing:** Direct API call for email queries (bypass AI)
- **Tool Badges:** Show which tools were used
- **Thinking Expander:** Toggle to see AI thinking process
- **Auto-scroll** to latest message

**Suggestion Pills:**

| Label | Prompt | Icon |
|-------|--------|------|
| Tasks của tôi | What are my pending tasks? | ClipboardList |
| Email mới nhất | Check my last email | Mail |
| Tạo quiz | Create a quiz about Python | Brain |
| Tin tech | Latest tech news | Newspaper |

---

### 3. `Message.tsx` - Message Rendering

**Đường dẫn:** `components/chat/Message.tsx`

**User Message:**

```
                        ┌──────────────────────┐
                        │  User text here...   │ ← rounded-2xl, right-aligned
                        └──────────────────────┘
```

- Background: `var(--surface-hover)`
- Max width: 75%
- Padding: 10px 16px

**Assistant Message:**

```
[🔧 search_gmail] [🔧 get_email]  ← Tool badges (optional)

Plain text response...            ← No bubble, left-aligned
Uses MarkdownRenderer
```

**Email List Detection:**

- If content matches email list pattern → Render `EmailCard`
- If content matches full email pattern → Render `EmailContent`
- Otherwise → Render with `MarkdownRenderer`

---

### 4. `EmailCard.tsx` - Email List UI

```
┌─────────────────────────────────────────────────┐
│ 📬 5 emails found                               │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ [1] 🟣 JD  | John Doe           | 2h ago   │ │
│ │            | Subject line here...          │ │
│ │            | Preview text...      [View →] │ │
│ └─────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────┐ │
│ │ [2] 🔵 AB  | Alice Bob          | 5h ago   │ │
│ │            | Another subject...            │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Avatar Colors:** Rotating (purple, blue, cyan, green, orange, pink)

---

## 🎨 Theme System

### CSS Variables (`globals.css`)

| Variable | Dark Mode | Light Mode |
|----------|-----------|------------|
| `--background` | `#09090b` | `#F5F1EB` (warm cream) |
| `--surface` | `#18181b` | `#FAF8F5` |
| `--surface-hover` | `#27272a` | `#EDE8E0` |
| `--border` | `#27272a` | `#E0D9CF` |
| `--text` | `#fafafa` | `#2D2A26` |
| `--text-muted` | `#a1a1aa` | `#5C564E` |
| `--text-dim` | `#71717a` | `#8A847A` |
| `--primary` | `#7c3aed` (purple) | `#6B8F71` (sage green) |

### Font Stack

```css
--font-heading: 'Google Sans', -apple-system, BlinkMacSystemFont, sans-serif;
--font-body: 'Google Sans', -apple-system, BlinkMacSystemFont, sans-serif;
```

### Theme Toggle

- **Options:** Light / Dark / System
- **Storage:** `localStorage` via Zustand persist
- **Key:** `emo-theme-storage`

---

## 🔌 State Management (Zustand)

### `useAppStore.ts`

```typescript
interface AppStore {
    sessions: ChatSession[];        // List of chat sessions
    isSidebarExpanded: boolean;     // Sidebar toggle
    isRecentsExpanded: boolean;     // Chat history toggle
    loadSessions: () => Promise;    // Fetch from backend
    deleteSession: (id) => Promise; // Delete session
}
```

### `useThemeStore.ts`

```typescript
interface ThemeStore {
    mode: 'light' | 'dark' | 'system';
    resolvedTheme: 'light' | 'dark';
    setMode: (mode) => void;
}
```

---

## 🔗 API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/stream` | GET (SSE) | Streaming chat response |
| `/api/chat/sessions` | GET | List all sessions |
| `/api/chat/sessions/{id}` | GET | Get session messages |
| `/api/chat/sessions/{id}` | DELETE | Delete session |
| `/api/emails/list` | GET | Direct email fetch (bypass AI) |

---

## 🎯 Design Patterns

### 1. **Copilot-style UI**

- Bold greeting on empty state
- Prominent input card with rounded corners
- Suggestion chips below input
- No message bubbles for assistant (clean text)

### 2. **Glassmorphism**

- Modal backdrops with blur (`backdrop-filter: blur(4px)`)
- Glass cards with semi-transparent backgrounds

### 3. **Micro-animations**

- `animate-fade-in`: Smooth message appearance
- `animate-slide-in`: Sidebar transitions
- `animate-pulse`: Loading dots
- Hover scale effects on buttons

### 4. **Accessibility**

- `aria-label` on all interactive elements
- `prefers-reduced-motion` media query respected
- Keyboard navigation (Enter to send)

---

## 📝 Notes for Future Development

1. **Input is duplicated** - Same textarea code in empty state and has-messages state
2. **Hardcoded greeting** - "Good morning, Josh!" should be dynamic
3. **Email detection uses regex** - May break with format changes
4. **Backend URL hardcoded** - Should use env variable
5. **Session limit** - Only shows last 10 sessions

---

## 🚀 Quick Reference: Adding New Features

### Add new suggestion chip

```typescript
// In ChatContainer.tsx SUGGESTIONS array
{ label: "Label", prompt: "AI prompt", icon: LucideIcon }
```

### Add new theme color

```css
/* In globals.css [data-theme="dark"] and [data-theme="light"] */
--new-color: #hexcode;
```

### Add new component

1. Create in `components/`
2. Export in `components/chat/index.ts` if chat-related
3. Import and use in `page.tsx` or `ChatContainer.tsx`
