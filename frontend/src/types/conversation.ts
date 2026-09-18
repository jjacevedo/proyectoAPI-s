export type ConversationSummary = {
  id: number;
  mode: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type MessageDetail = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
};

export type ConversationListResponse = { conversations: ConversationSummary[] };

export type MessageListResponse = { conversation_id: number; messages: MessageDetail[] };
