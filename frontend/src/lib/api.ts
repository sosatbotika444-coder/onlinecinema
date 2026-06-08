import type { PublicRoom, Room, RoomSession, Video } from "../types";

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const SOCKET_URL = (import.meta.env.VITE_SOCKET_URL || API_URL).replace(/\/$/, "");

interface RequestOptions extends RequestInit {
  token?: string;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = "Request failed";
    try {
      const error = await response.json();
      message = error.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function createRoom(payload: {
  name: string;
  nickname: string;
  avatar_url?: string | null;
  max_participants: number;
  password?: string | null;
  is_private: boolean;
}) {
  return request<RoomSession>("/api/rooms", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function joinRoom(
  code: string,
  payload: { nickname: string; avatar_url?: string | null; password?: string | null }
) {
  return request<RoomSession>(`/api/rooms/${code.toUpperCase()}/join`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getRoom(code: string) {
  return request<Room>(`/api/rooms/${code.toUpperCase()}`);
}

export function listPublicRooms() {
  return request<PublicRoom[]>("/api/rooms/public");
}

export function addVideoLink(code: string, token: string, url: string, title?: string) {
  return request<Video>(`/api/rooms/${code.toUpperCase()}/videos`, {
    method: "POST",
    token,
    body: JSON.stringify({ url, title })
  });
}

export async function presignUpload(
  token: string,
  payload: { room_code: string; filename: string; content_type: string; size_bytes: number }
) {
  return request<{
    upload_url: string;
    fields: Record<string, string>;
    method: "POST";
    storage_key: string;
    public_url: string | null;
    max_size_bytes: number;
  }>("/api/uploads/presign", {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export function completeUpload(
  token: string,
  payload: {
    room_code: string;
    storage_key: string;
    filename: string;
    content_type: string;
    size_bytes: number;
    public_url: string | null;
  }
) {
  return request<Video>("/api/uploads/complete", {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export function uploadToS3(
  uploadUrl: string,
  fields: Record<string, string>,
  file: File,
  onProgress: (progress: number) => void
) {
  return new Promise<void>((resolve, reject) => {
    const form = new FormData();
    Object.entries(fields).forEach(([field, value]) => form.append(field, value));
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", uploadUrl);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed with status ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Upload failed"));
    xhr.send(form);
  });
}
