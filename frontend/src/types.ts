export type SourceType = "youtube" | "vk" | "rutube" | "direct" | "upload";

export interface Participant {
  id: string;
  nickname: string;
  avatar_url: string | null;
  is_owner: boolean;
  is_online: boolean;
  last_seen: string;
}

export interface Video {
  id: string;
  source_type: SourceType;
  url: string;
  embed_url: string | null;
  title: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  created_at: string;
}

export interface PlaybackState {
  is_playing: boolean;
  position: number;
  updated_at: string | null;
}

export interface Room {
  id: string;
  code: string;
  name: string;
  max_participants: number;
  is_private: boolean;
  owner_id: string | null;
  current_video: Video | null;
  participants: Participant[];
  playback: PlaybackState;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  participant_id: string | null;
  nickname: string | null;
  message_type: "user" | "system";
  body: string;
  created_at: string;
}

export interface RoomSession {
  room: Room;
  participant: Participant;
  token: string;
  invite_link: string;
}

export interface PublicRoom {
  code: string;
  name: string;
  online_count: number;
  max_participants: number;
  has_video: boolean;
  created_at: string;
}
