import { motion } from "framer-motion";
import { Clapperboard, CloudUpload, Film, Globe2, MessageCircle, Play, RadioTower, Users, Video } from "lucide-react";
import { useEffect, useState } from "react";

import Button from "../components/Button";
import Modal from "../components/Modal";
import { CreateRoomForm, JoinRoomForm } from "../components/RoomForms";
import { listPublicRooms } from "../lib/api";
import type { PublicRoom } from "../types";

const features = [
  { label: "Синхронный просмотр", icon: RadioTower },
  { label: "Общий чат", icon: MessageCircle },
  { label: "Поддержка YouTube", icon: Play },
  { label: "Поддержка VK Видео", icon: Video },
  { label: "Поддержка Rutube", icon: Globe2 },
  { label: "Загрузка собственных файлов", icon: CloudUpload },
  { label: "До 4 участников", icon: Users }
];

export default function LandingPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);
  const [joinCode, setJoinCode] = useState("");
  const [rooms, setRooms] = useState<PublicRoom[]>([]);

  useEffect(() => {
    listPublicRooms().then(setRooms).catch(() => setRooms([]));
  }, []);

  function openJoin(code?: string) {
    setJoinCode(code || "");
    setJoinOpen(true);
  }

  return (
    <main className="landing-page">
      <section className="hero-section">
        <div className="hero-bg" />
        <nav className="top-nav">
          <div className="brand">
            <span className="brand-mark">
              <Clapperboard size={22} />
            </span>
            <span>SexParty</span>
          </div>
          <Button variant="ghost" onClick={() => openJoin()}>
            Войти по коду
          </Button>
        </nav>

        <motion.div
          className="hero-content"
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
        >
          <span className="hero-kicker">Private watch rooms · realtime sync</span>
          <h1>Смотрите фильмы вместе, где бы вы ни находились</h1>
          <p>
            Создавайте комнаты, приглашайте друзей и смотрите любимые фильмы синхронно в режиме реального времени.
          </p>
          <div className="hero-actions">
            <Button icon={<Film size={19} />} onClick={() => setCreateOpen(true)}>
              Создать комнату
            </Button>
            <Button variant="secondary" icon={<Users size={19} />} onClick={() => openJoin()}>
              Присоединиться к комнате
            </Button>
          </div>
        </motion.div>
      </section>

      <section className="feature-band">
        <div className="feature-grid">
          {features.map(({ label, icon: Icon }) => (
            <motion.div
              className="feature-card"
              key={label}
              whileHover={{ y: -4, scale: 1.01 }}
              transition={{ type: "spring", stiffness: 260, damping: 20 }}
            >
              <Icon size={22} />
              <span>{label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="public-rooms-section">
        <div className="section-heading">
          <span className="eyebrow">Публичные комнаты</span>
          <h2>Подключайтесь к открытым просмотрам</h2>
        </div>
        <div className="public-room-grid">
          {rooms.length === 0 && (
            <div className="empty-public">
              <p>Публичных комнат пока нет. Создайте первую и включите открытый доступ.</p>
            </div>
          )}
          {rooms.map((room) => (
            <button className="public-room-card" key={room.code} onClick={() => openJoin(room.code)}>
              <strong>{room.name}</strong>
              <span>{room.online_count}/{room.max_participants} онлайн</span>
              <small>{room.has_video ? "Видео выбрано" : "Ожидает видео"} · {room.code}</small>
            </button>
          ))}
        </div>
      </section>

      <Modal title="Создать комнату" open={createOpen} onClose={() => setCreateOpen(false)}>
        <CreateRoomForm onDone={() => setCreateOpen(false)} />
      </Modal>
      <Modal title="Присоединиться" open={joinOpen} onClose={() => setJoinOpen(false)}>
        <JoinRoomForm initialCode={joinCode} onDone={() => setJoinOpen(false)} />
      </Modal>
    </main>
  );
}
