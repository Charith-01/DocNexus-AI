import type {
  AuthToken,
  DocumentList,
  RouteResult,
  UploadResult,
  User,
} from "../types/api";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const TOKEN_KEY = "docnexus_access_token";

export const session = {
  getToken: () => sessionStorage.getItem(TOKEN_KEY),
  setToken: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (authenticated) {
    const token = session.getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 401 && authenticated) {
    session.clear();
    window.dispatchEvent(new Event("docnexus:auth-expired"));
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "Request failed");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthToken>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/auth/me", {}, true),

  listDocuments: () => request<DocumentList>("/documents", {}, true),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResult>(
      "/documents/upload",
      { method: "POST", body: form },
      true,
    );
  },

  deleteDocument: (documentId: string) =>
    request<void>(`/documents/${documentId}`, { method: "DELETE" }, true),

  routeQuery: (query: string, documentIds: string[]) =>
    request<RouteResult>(
      "/orchestrator/route",
      { method: "POST", body: JSON.stringify({ query, document_ids: documentIds }) },
      true,
    ),
};
