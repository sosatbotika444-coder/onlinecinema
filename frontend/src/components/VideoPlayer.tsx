import { Pause, Play, Radio, Tv } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Socket } from "socket.io-client";

import type { PlaybackState, Video } from "../types";

declare global {
  interface Window {
    YT?: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

interface VideoPlayerProps {
  video: Video | null;
  playback: PlaybackState;
  isOwner: boolean;
  socket: Socket | null;
}

function youtubeId(embedUrl: string | null, url: string) {
  const target = embedUrl || url;
  const match = target.match(/(?:embed\/|v=|youtu\.be\/)([A-Za-z0-9_-]{6,})/);
  return match?.[1] || "";
}

function ensureYouTubeApi() {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  return new Promise<any>((resolve) => {
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previous?.();
      resolve(window.YT);
    };
    if (!document.querySelector('script[src="https://www.youtube.com/iframe_api"]')) {
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      document.body.appendChild(script);
    }
  });
}

export default function VideoPlayer({ video, playback, isOwner, socket }: VideoPlayerProps) {
  const htmlVideoRef = useRef<HTMLVideoElement | null>(null);
  const youtubeHostRef = useRef<HTMLDivElement | null>(null);
  const youtubePlayerRef = useRef<any>(null);
  const applyingRemoteRef = useRef(false);
  const [ready, setReady] = useState(false);

  const providerLabel = useMemo(() => {
    if (!video) return "Видео не выбрано";
    if (video.source_type === "upload") return "Загруженный файл";
    if (video.source_type === "direct") return "Прямая ссылка";
    if (video.source_type === "youtube") return "YouTube";
    if (video.source_type === "vk") return "VK Видео";
    return "Rutube";
  }, [video]);

  useEffect(() => {
    const element = htmlVideoRef.current;
    if (!element || !video || !["direct", "upload"].includes(video.source_type)) return;

    applyingRemoteRef.current = true;
    if (Math.abs(element.currentTime - playback.position) > 1.1) {
      element.currentTime = Math.max(playback.position, 0);
    }
    if (playback.is_playing) {
      element.play().catch(() => undefined);
    } else {
      element.pause();
    }
    window.setTimeout(() => {
      applyingRemoteRef.current = false;
    }, 220);
  }, [playback.is_playing, playback.position, playback.updated_at, video]);

  useEffect(() => {
    if (!video || video.source_type !== "youtube") return;
    const id = youtubeId(video.embed_url, video.url);
    if (!id || !youtubeHostRef.current) return;
    let cancelled = false;

    ensureYouTubeApi().then((YT) => {
      if (cancelled || !youtubeHostRef.current) return;
      youtubePlayerRef.current?.destroy?.();
      youtubePlayerRef.current = new YT.Player(youtubeHostRef.current, {
        videoId: id,
        playerVars: { playsinline: 1, modestbranding: 1, rel: 0 },
        events: {
          onReady: () => setReady(true),
          onStateChange: (event: any) => {
            if (!isOwner || applyingRemoteRef.current) return;
            const position = youtubePlayerRef.current?.getCurrentTime?.() || 0;
            if (event.data === YT.PlayerState.PLAYING) socket?.emit("playback:play", { position });
            if (event.data === YT.PlayerState.PAUSED) socket?.emit("playback:pause", { position });
          }
        }
      });
    });

    return () => {
      cancelled = true;
      setReady(false);
      youtubePlayerRef.current?.destroy?.();
      youtubePlayerRef.current = null;
    };
  }, [isOwner, socket, video]);

  useEffect(() => {
    const player = youtubePlayerRef.current;
    if (!player || !ready || video?.source_type !== "youtube") return;
    applyingRemoteRef.current = true;
    const current = player.getCurrentTime?.() || 0;
    if (Math.abs(current - playback.position) > 1.3) player.seekTo(Math.max(playback.position, 0), true);
    if (playback.is_playing) player.playVideo?.();
    else player.pauseVideo?.();
    window.setTimeout(() => {
      applyingRemoteRef.current = false;
    }, 240);
  }, [playback.is_playing, playback.position, playback.updated_at, ready, video?.source_type]);

  function emitPlay() {
    if (isOwner && !applyingRemoteRef.current) {
      socket?.emit("playback:play", { position: htmlVideoRef.current?.currentTime || 0 });
    }
  }

  function emitPause() {
    if (isOwner && !applyingRemoteRef.current) {
      socket?.emit("playback:pause", { position: htmlVideoRef.current?.currentTime || 0 });
    }
  }

  function emitSeek() {
    if (isOwner && !applyingRemoteRef.current) {
      socket?.emit("playback:seek", { position: htmlVideoRef.current?.currentTime || 0 });
    }
  }

  return (
    <section className="player-shell">
      <div className="player-topbar">
        <div>
          <span className="eyebrow">
            <Radio size={14} /> {providerLabel}
          </span>
          <h1>{video?.title || "Выберите видео для комнаты"}</h1>
        </div>
        <div className="sync-pill">
          {playback.is_playing ? <Play size={16} /> : <Pause size={16} />}
          {playback.is_playing ? "Синхронно идёт" : "На паузе"}
        </div>
      </div>

      <div className="video-frame">
        {!video && (
          <div className="empty-player">
            <Tv size={54} />
            <p>Владелец комнаты может добавить YouTube, VK Видео, Rutube, прямую ссылку или файл.</p>
          </div>
        )}

        {video && ["direct", "upload"].includes(video.source_type) && (
          <video
            ref={htmlVideoRef}
            src={video.url}
            controls
            playsInline
            preload="metadata"
            onPlay={emitPlay}
            onPause={emitPause}
            onSeeked={emitSeek}
          />
        )}

        {video?.source_type === "youtube" && <div className="youtube-host" ref={youtubeHostRef} />}

        {video && ["vk", "rutube"].includes(video.source_type) && (
          <iframe
            title={video.title || providerLabel}
            src={video.embed_url || video.url}
            allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
            allowFullScreen
          />
        )}
      </div>
    </section>
  );
}
