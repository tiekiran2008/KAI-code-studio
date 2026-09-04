# Frontend Architecture

This document outlines the architecture for Phase 9: Production-Grade Frontend Platform.

## Architectural Overview

The frontend is built using **React 19**, **TypeScript**, **Vite**, **Tailwind CSS**, **React Router v7**, **Zustand**, and **TanStack Query**. It strictly adheres to Clean Architecture principles by separating the UI component layer from API services and state management stores.

```
src/
├── api/                   # API Data Access & Client Wrappers
│   ├── client.ts          # Backend API endpoints + Mock Fallback providers
│   └── mockData.ts        # Production fallback telemetry data
├── components/            # Reusable UI & Layout Components
│   ├── common/            # Command Palette (Cmd+K), Toast Notifications
│   └── layout/            # AppLayout (Sidebar, Header, Breadcrumbs)
├── pages/                 # 8 Dedicated Platform Pages
│   ├── DashboardPage.tsx
│   ├── RepositoryManagerPage.tsx
│   ├── WorkspacePage.tsx
│   ├── AgentMonitorPage.tsx
│   ├── MemoryCenterPage.tsx
│   ├── ToolActivityPage.tsx
│   ├── AnalyticsPage.tsx
│   └── SettingsPage.tsx
├── store/                 # Zustand Global State Management
│   ├── useUIStore.ts      # Theme, Modals, Sidebar, Toasts
│   ├── useRepoStore.ts    # Repositories, Branches, File Tree, Editor Tabs
│   ├── useChatStore.ts    # Session state, streaming messages, agent traces
│   └── useSettingsStore.ts# LLM provider configuration, user preferences
├── types/                 # TypeScript Domain Models & Interfaces
├── App.tsx                # React Router Path Mapping
├── index.css              # Glassmorphic Tailwind Design Tokens
└── main.tsx               # Application Bootstrap & TanStack Query Provider
```

## State Management Architecture (Zustand Stores)

1. **`useUIStore`**: Manages volatile UI states (Dark/Light mode, sidebar collapse, active modals, command palette visibility, and toast alert queues).
2. **`useRepoStore`**: Manages selected codebase repository, active branch, directory tree hierarchy, open editor tabs, and selected code file.
3. **`useChatStore`**: Controls active AI engineering session, message thread history, multi-agent reasoning steps, tool invocation badges, and source citations.
4. **`useSettingsStore`**: Persists local LLM settings (Provider, model name, API key, FastAPI endpoint base URL) and code editor preferences.

## Monaco Editor & Split Workspace Layout

The **AI Workspace** page (`/workspace`) features a 3-column resizable layout:
- **Left Panel**: Repository File Explorer with file search and branch switcher.
- **Center Panel**: Monaco Code Editor (`@monaco-editor/react`) featuring syntax highlighting, tabbed file navigation, and line viewing.
- **Right Panel**: Production AI Chat Panel rendering Markdown, multi-agent execution step trace accordions, RAG source citations, and suggested quick action chips.
