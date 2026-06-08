import { Crown, Send, Signal, SignalZero } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import type { ChatMessage, Participant, Room } from "../types";
import Button from "./Button";

interface RoomSidebarProps {
  room: Room;
  messages: ChatMessage[];
  self: Participant;
  typingName: string;
  onSend: (message: string) => void;
  onTyping: (typing: boolean) => void;
}

const emojis = ["🍿", "😂", "🔥", "💜", "😱"];

export default function RoomSidebar({ room, messages, self, typingName, onSend, onTyping }: RoomSidebarProps) {
  const [message, setMessage] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const typingTimer = useRef<number | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setMessage("");
    onTyping(false);
  }

  function updateMessage(value: string) {
    setMessage(value);
    onTyping(true);
    if (typingTimer.current) window.clearTimeout(typingTimer.current);
    typingTimer.current = window.setTimeout(() => onTyping(false), 900);
  }

  return (
    <aside className="room-sidebar">
      <section className="participants-panel">
        <div className="panel-title">
          <h2>Участники</h2>
          <span>{room.participants.filter((participant) => participant.is_online).length}/{room.max_participants}</span>
        </div>
        <div className="participant-list">
          {room.participants.map((participant) => (
            <div className="participant-row" key={participant.id}>
              <div className="avatar">
                {participant.avatar_url ? <img src={participant.avatar_url} alt="" /> : participant.nickname[0]?.toUpperCase()}
              </div>
              <div>
                <strong>{participant.nickname}{participant.id === self.id ? " · вы" : ""}</strong>
                <span>{participant.is_owner ? "Владелец комнаты" : "Гость"}</span>
              </div>
              <div className="participant-icons">
                {participant.is_owner && <Crown size={15} />}
                {participant.is_online ? <Signal size={15} className="online" /> : <SignalZero size={15} className="offline" />}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="chat-panel">
        <div className="panel-title">
          <h2>Чат</h2>
          {typingName && <span>{typingName} печатает...</span>}
        </div>
        <div className="chat-feed" ref={scrollRef}>
          {messages.map((item) => (
            <div className={`chat-message chat-message--${item.message_type}`} key={item.id}>
              {item.message_type === "user" && <strong>{item.nickname || "Гость"}</strong>}
              <p>{item.body}</p>
            </div>
          ))}
        </div>
        <div className="emoji-row">
          {emojis.map((emoji) => (
            <button key={emoji} type="button" onClick={() => updateMessage(`${message}${emoji}`)}>
              {emoji}
            </button>
          ))}
        </div>
        <form className="chat-form" onSubmit={submit}>
          <input
            value={message}
            maxLength={500}
            placeholder="Написать сообщение"
            onChange={(event) => updateMessage(event.target.value)}
          />
          <Button aria-label="Отправить" icon={<Send size={17} />} />
        </form>
      </section>
    </aside>
  );
}
