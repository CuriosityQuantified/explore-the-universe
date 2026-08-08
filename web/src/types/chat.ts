export interface ChatObjectResult {
  uuid: string;
  type: string | null;
  catalog_name: string | null;
  thumbnail_url: string | null;
  detail_url: string;
}

export interface ChatResponse {
  answer: string;
  objects: ChatObjectResult[];
  query_executed: Record<string, unknown> | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  objects?: ChatObjectResult[];
  query_executed?: Record<string, unknown> | null;
}
