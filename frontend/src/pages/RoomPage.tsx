import { ArrowLeft, Copy, ShieldCheck, Wifi, WifiOff } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { io, Socket } from "socket.io-client";

import Button from "../components/Button";
import { JoinRoomForm } from "../components/RoomForms";
import RoomSidebar from "../components/RoomSidebar";
import VideoPanel from "../components/VideoPanel";
import VideoPlayer from "../components/VideoPlayer";
import { getRoom, SOCKET_URL } from "../lib/api";
import { readRoomSession } from "../lib/session";
import type { ChatMessage, PlaybackState, Room } from "../types";

export default function RoomPage() {
  const params = useParams();
  const code = (params.code || "").toUpperCase();
  const [room, setRoom] = useState<Room | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [session, setSession] = useState(() => readRoomSession(code));
  const [connected, setConnected] = useState(false);
  const [typingName, setTypingName] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getRoom(code).then(setRoom).catch((error) => setNotice(error instanceof Error ? error.message : "Комната не найдена"));
  }, [code]);

  useEffect(() => {
    if (!session?.token) return;
    const client = io(SOCKET_URL, {
      path: "/socket.io",
      auth: { token: session.token },
      transports: ["websocket", "polling"],
      reconnectionAttempts: Infinity,
      reconnectionDelay: 650
    });

    client.on("connect", () => {
      setConnected(true);
      client.emit("room:join");
    });
    client.on("disconnect", () => setConnected(false));
    client.on("room:state", (nextRoom: Room) => setRoom(nextRoom));
    client.on("chat:history", (history: ChatMessage[]) => setMessages(history));
    client.on("chat:message", (message: ChatMessage) => {
      setMessages((current) => (current.some((item) => item.id === message.id) ? current : [...current, message]));
      if (message.message_type === "system") {
        setNotice(message.body);
        window.setTimeout(() => setNotice(""), 2600);
      }
    });
    client.on("system:notice", (message: ChatMessage) => {
      setNotice(message.body);
      window.setTimeout(() => setNotice(""), 2600);
    });
    client.on("playback:state", (playback: PlaybackState) => {
      setRoom((current) => (current ? { ...current, playback } : current));
    });
    client.on("video:change", () => client.emit("room:join"));
    client.on("chat:typing", (payload: { nickname: string; typing: boolean }) => {
      setTypingName(payload.typing ? payload.nickname : "");
      if (payload.typing) window.setTimeout(() => setTypingName(""), 1200);
    });
    client.on("error:notice", (payload: { message: string }) => {
      setNotice(payload.message);
      window.setTimeout(() => setNotice(""), 2600);
    });

    const heartbeat = window.setInterval(() => client.emit("presence:heartbeat"), 12_000);
    setSocket(client);

    return () => {
      window.clearInterval(heartbeat);
      client.disconnect();
      setSocket(null);
      setConnected(false);
    };
  }, [session?.token]);

  const isOwner = useMemo(() => {
    if (!room || !session) return false;
    return session.participant.is_owner || session.participant.id === room.owner_id;
  }, [room, session]);

  if (!session || !room) {
    return (
      <main className="room-page room-page--gate">
        <Link className="back-link" to="/">
          <ArrowLeft size={17} /> На главную
        </Link>
        <div className="join-gate">
          <span className="eyebrow">Комната {code}</span>
          <h1>{room?.name || "Подключение к комнате"}</h1>
          {notice && <p className="form-error">{notice}</p>}
          <JoinRoomForm
            initialCode={code}
            onDone={() => {
              setSession(readRoomSession(code));
            }}
          />
        </div>
      </main>
    );
  }

  const inviteLink = session.invite_link || `${window.location.origin}/room/${room.code}`;

  return (
    <main className="room-page">
      <header className="room-header">
        <Link className="back-link" to="/">
          <ArrowLeft size={17} /> SexParty
        </Link>
        <div className="room-meta">
          <strong>{room.name}</strong>
          <span>{room.code}</span>
        </div>
        <div className="room-actions">
          <span className={`connection-badge ${connected ? "online" : "offline"}`}>
            {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
            {connected ? "Онлайн" : "Оффлайн"}
          </span>
          {isOwner && (
            <span className="owner-badge">
              <ShieldCheck size={16} /> Владелец
            </span>
          )}
          <Button variant="ghost" icon={<Copy size={16} />} onClick={() => navigator.clipboard.writeText(inviteLink)}>
            Инвайт
          </Button>
        </div>
      </header>

      {notice && <div className="toast-notice">{notice}</div>}

      <div className="watch-layout">
        <div className="watch-main">
          <VideoPlayer video={room.current_video} playback={room.playback} isOwner={isOwner} socket={socket} />
          <VideoPanel code={room.code} token={session.token} inviteLink={inviteLink} isOwner={isOwner} socket={socket} />
        </div>
        <RoomSidebar
          room={room}
          messages={messages}
          self={session.participant}
          typingName={typingName}
          onSend={(body) => socket?.emit("chat:message", { body })}
          onTyping={(typing) => socket?.emit("chat:typing", { typing })}
        />
      </div>
    </main>
  );
}
