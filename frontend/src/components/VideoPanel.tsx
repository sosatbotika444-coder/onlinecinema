import { Link2, UploadCloud } from "lucide-react";
import { FormEvent, useState } from "react";
import type { Socket } from "socket.io-client";

import { addVideoLink, completeUpload, presignUpload, uploadToS3 } from "../lib/api";
import Button from "./Button";

interface VideoPanelProps {
  code: string;
  token: string;
  inviteLink: string;
  isOwner: boolean;
  socket: Socket | null;
}

export default function VideoPanel({ code, token, inviteLink, isOwner, socket }: VideoPanelProps) {
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const [copied, setCopied] = useState(false);

  async function copyInvite() {
    await navigator.clipboard.writeText(inviteLink || `${window.location.origin}/room/${code}`);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  async function submitLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const url = String(form.get("url") || "");
    try {
      const video = await addVideoLink(code, token, url);
      socket?.emit("video:change", { video_id: video.id });
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить видео");
    }
  }

  async function selectFile(file: File | null) {
    if (!file) return;
    setError("");
    setProgress(1);
    try {
      const contentType = file.type || "application/octet-stream";
      const presigned = await presignUpload(token, {
        room_code: code,
        filename: file.name,
        content_type: contentType,
        size_bytes: file.size
      });
      await uploadToS3(presigned.upload_url, presigned.fields, file, setProgress);
      const video = await completeUpload(token, {
        room_code: code,
        storage_key: presigned.storage_key,
        filename: file.name,
        content_type: contentType,
        size_bytes: file.size,
        public_url: presigned.public_url
      });
      socket?.emit("video:change", { video_id: video.id });
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить файл");
      setProgress(0);
    }
  }

  return (
    <section className="video-panel">
      <div className="panel-title">
        <h2>Контент</h2>
        <Button variant="ghost" onClick={copyInvite}>
          {copied ? "Скопировано" : "Инвайт"}
        </Button>
      </div>

      {isOwner ? (
        <>
          <form className="inline-source-form" onSubmit={submitLink}>
            <input name="url" type="url" required placeholder="YouTube, VK, Rutube или mp4/webm" />
            <Button icon={<Link2 size={17} />}>Добавить</Button>
          </form>
          <label className="upload-drop">
            <UploadCloud size={22} />
            <span>Загрузить MP4, MKV, MOV, AVI или WEBM</span>
            <input
              type="file"
              accept=".mp4,.mkv,.mov,.avi,.webm,video/mp4,video/webm,video/quicktime"
              onChange={(event) => selectFile(event.target.files?.[0] || null)}
            />
          </label>
          {progress > 0 && (
            <div className="upload-progress" aria-label="Прогресс загрузки">
              <span style={{ width: `${progress}%` }} />
            </div>
          )}
          {error && <p className="form-error">{error}</p>}
        </>
      ) : (
        <p className="muted-copy">Видео выбирает владелец комнаты. Инвайт доступен для приглашения друзей.</p>
      )}
    </section>
  );
}
