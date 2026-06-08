import { Lock, LogIn, Plus, Users } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createRoom, joinRoom } from "../lib/api";
import { saveRoomSession } from "../lib/session";
import Button from "./Button";

interface CreateRoomFormProps {
  onDone?: () => void;
}

export function CreateRoomForm({ onDone }: CreateRoomFormProps) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const form = new FormData(event.currentTarget);
    try {
      const session = await createRoom({
        name: String(form.get("name") || ""),
        nickname: String(form.get("nickname") || ""),
        avatar_url: String(form.get("avatar_url") || "") || null,
        max_participants: Number(form.get("max_participants") || 4),
        password: String(form.get("password") || "") || null,
        is_private: form.get("is_private") === "on"
      });
      saveRoomSession(session);
      onDone?.();
      navigate(`/room/${session.room.code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать комнату");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="stack-form" onSubmit={submit}>
      <label>
        <span>Название комнаты</span>
        <input name="name" minLength={2} maxLength={120} required placeholder="Кино в пятницу" />
      </label>
      <label>
        <span>Ваш никнейм</span>
        <input name="nickname" minLength={2} maxLength={40} required placeholder="Алекс" />
      </label>
      <label>
        <span>Аватар URL</span>
        <input name="avatar_url" type="url" placeholder="https://..." />
      </label>
      <div className="form-grid">
        <label>
          <span>Участники</span>
          <select name="max_participants" defaultValue="4">
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
          </select>
        </label>
        <label>
          <span>Пароль</span>
          <input name="password" type="password" minLength={4} maxLength={80} placeholder="Необязательно" />
        </label>
      </div>
      <label className="switch-line">
        <input name="is_private" type="checkbox" defaultChecked />
        <span>Приватная комната</span>
      </label>
      {error && <p className="form-error">{error}</p>}
      <Button disabled={loading} icon={<Plus size={18} />}>
        {loading ? "Создаём..." : "Создать комнату"}
      </Button>
    </form>
  );
}

interface JoinRoomFormProps {
  initialCode?: string;
  onDone?: () => void;
}

export function JoinRoomForm({ initialCode = "", onDone }: JoinRoomFormProps) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const form = new FormData(event.currentTarget);
    const code = String(form.get("code") || initialCode).trim().toUpperCase();
    try {
      const session = await joinRoom(code, {
        nickname: String(form.get("nickname") || ""),
        avatar_url: String(form.get("avatar_url") || "") || null,
        password: String(form.get("password") || "") || null
      });
      saveRoomSession(session);
      onDone?.();
      navigate(`/room/${session.room.code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти в комнату");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="stack-form" onSubmit={submit}>
      {!initialCode && (
        <label>
          <span>Код комнаты</span>
          <input name="code" minLength={4} maxLength={12} required placeholder="A1B2C3D4" />
        </label>
      )}
      <label>
        <span>Ваш никнейм</span>
        <input name="nickname" minLength={2} maxLength={40} required placeholder="Максим" />
      </label>
      <label>
        <span>Аватар URL</span>
        <input name="avatar_url" type="url" placeholder="https://..." />
      </label>
      <label>
        <span>Пароль</span>
        <input name="password" type="password" maxLength={80} placeholder="Если нужен" />
      </label>
      {error && <p className="form-error">{error}</p>}
      <Button disabled={loading} icon={<LogIn size={18} />}>
        {loading ? "Входим..." : "Присоединиться"}
      </Button>
      <div className="form-hints">
        <span>
          <Users size={15} /> До 4 участников
        </span>
        <span>
          <Lock size={15} /> Пароль опционален
        </span>
      </div>
    </form>
  );
}
