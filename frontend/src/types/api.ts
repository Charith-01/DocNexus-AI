export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface DocumentRecord {
  id: string;
  owner_id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  sha256: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  documents: DocumentRecord[];
  total: number;
}

export interface UploadResult {
  message: string;
  document: DocumentRecord;
}

export interface RouteResult {
  request_id: string;
  intent: string;
  target_agent: string;
  next_steps: string[];
}
