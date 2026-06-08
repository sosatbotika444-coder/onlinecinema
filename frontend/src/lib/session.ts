import type { Participant, RoomSession } from "../types";

export interface StoredSession {
  token: string;
  participant: Participant;
  invite_link: string;
}

const key = (code: string) => `sexparty:room:${code.toUpperCase()}`;

export function saveRoomSession(session: RoomSession) {
  localStorage.setItem(
    key(session.room.code),
    JSON.stringify({
      token: session.token,
      participant: session.participant,
      invite_link: session.invite_link
    })
  );
}

export function readRoomSession(code: string): StoredSession | null {
  const raw = localStorage.getItem(key(code));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredSession;
  } catch {
    localStorage.removeItem(key(code));
    return null;
  }
}

export function clearRoomSession(code: string) {
  localStorage.removeItem(key(code));
}
