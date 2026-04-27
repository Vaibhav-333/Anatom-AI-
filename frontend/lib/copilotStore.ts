import { create } from "zustand";

export interface CopilotMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: string;
  isStreaming?: boolean;
}

export interface CopilotConversation {
  id: string;
  title: string;
  reportId?: string;
  updatedAt: string;
}

interface CopilotState {
  // UI state
  isOpen: boolean;
  isWindowOpen: boolean;
  isClosing: boolean;

  // Conversation state
  conversationId: string | null;
  messages: CopilotMessage[];
  isStreaming: boolean;
  streamingContent: string;

  // Context
  currentReportId: string | null;
  currentPage: string;
  suggestedQuestions: string[];

  // Conversation list
  conversations: CopilotConversation[];

  // Actions
  openTray: () => void;
  openWindow: () => void;
  closeAll: () => void;
  setCurrentReportId: (id: string | null) => void;
  setCurrentPage: (page: string) => void;
  setConversationId: (id: string) => void;
  addUserMessage: (content: string) => string;
  startStreamingMessage: () => string;
  appendStreamToken: (id: string, token: string) => void;
  finalizeStreamingMessage: (id: string) => void;
  setSuggestedQuestions: (qs: string[]) => void;
  setConversations: (convs: CopilotConversation[]) => void;
  loadHistory: (msgs: CopilotMessage[]) => void;
  clearMessages: () => void;
  newConversation: () => void;
}

export const useCopilotStore = create<CopilotState>((set, get) => ({
  isOpen: false,
  isWindowOpen: false,
  isClosing: false,

  conversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: "",

  currentReportId: null,
  currentPage: "dashboard",
  suggestedQuestions: [
    "Is this normal for my age?",
    "What should I improve?",
    "Any diet suggestions?",
    "Compare with my last report",
  ],

  conversations: [],

  openTray: () => set({ isOpen: true, isClosing: false }),

  openWindow: () => set({ isOpen: true, isWindowOpen: true, isClosing: false }),

  closeAll: () => {
    set({ isClosing: true });
    // Staged animation: window → tray → button
    setTimeout(() => set({ isWindowOpen: false }), 0);
    setTimeout(() => set({ isOpen: false }), 600);
    setTimeout(() => set({ isClosing: false }), 900);
  },

  setCurrentReportId: (id) => set({ currentReportId: id }),
  setCurrentPage: (page) => set({ currentPage: page }),

  setConversationId: (id) => set({ conversationId: id }),

  addUserMessage: (content) => {
    const id = crypto.randomUUID();
    set((s) => ({
      messages: [...s.messages, { id, role: "user", content }],
    }));
    return id;
  },

  startStreamingMessage: () => {
    const id = crypto.randomUUID();
    set((s) => ({
      isStreaming: true,
      streamingContent: "",
      messages: [
        ...s.messages,
        { id, role: "assistant", content: "", isStreaming: true },
      ],
    }));
    return id;
  },

  appendStreamToken: (id, token) => {
    set((s) => ({
      streamingContent: s.streamingContent + token,
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    }));
  },

  finalizeStreamingMessage: (id) => {
    set((s) => ({
      isStreaming: false,
      streamingContent: "",
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m
      ),
    }));
  },

  setSuggestedQuestions: (qs) => set({ suggestedQuestions: qs }),

  setConversations: (convs) => set({ conversations: convs }),

  loadHistory: (msgs) => set({ messages: msgs }),

  clearMessages: () => set({ messages: [] }),

  newConversation: () =>
    set({
      conversationId: null,
      messages: [],
      streamingContent: "",
      isStreaming: false,
    }),
}));
