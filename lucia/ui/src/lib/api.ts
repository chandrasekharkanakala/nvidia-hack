import type { Session, Message, SystemMetrics } from "../types";

const BASE = "/api";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function getHealth() {
  return fetchJSON<{ status: string }>(`${BASE}/health`);
}

export function getSessions() {
  return fetchJSON<Session[]>(`${BASE}/sessions`);
}

export function getSessionMessages(sessionId: string) {
  return fetchJSON<Message[]>(`${BASE}/sessions/${sessionId}/messages`);
}

export function deleteSession(sessionId: string) {
  return fetch(`${BASE}/sessions/${sessionId}`, { method: "DELETE" });
}

export function getMetrics() {
  return fetchJSON<SystemMetrics>(`${BASE}/metrics`);
}

export async function postSTT(audio: Blob): Promise<string> {
  const form = new FormData();
  form.append("file", audio, "recording.webm");
  const res = await fetch(`${BASE}/voice/stt`, { method: "POST", body: form });
  if (!res.ok) throw new Error("STT failed");
  const data = await res.json();
  return data.text;
}
