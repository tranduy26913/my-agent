import type { Segment } from "./types";

/** 3725 -> "1:02:05"; 65 -> "1:05". */
export function fmtClock(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = String(s % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${r}` : `${m}:${r}`;
}

function srtTime(sec: number): string {
  const ms = Math.round(Math.max(0, sec) * 1000);
  const p = (n: number, w = 2) => String(n).padStart(w, "0");
  return `${p(Math.floor(ms / 3_600_000))}:${p(Math.floor(ms / 60_000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`;
}

/** "A" -> "Người A". Không biết tên thật: chỉ phân biệt giọng, nên người dùng tự đối chiếu ai là ai. */
export const speakerName = (s: Segment) => (s.speaker ? `Người ${s.speaker}` : null);

const withSpeaker = (s: Segment) => (s.speaker ? `${speakerName(s)}: ${s.text}` : s.text);

export const toPlainText = (segs: Segment[]) => segs.map((s) => `[${fmtClock(s.start)}] ${withSpeaker(s)}`).join("\n");

export const toSrt = (segs: Segment[]) =>
  segs.map((s, i) => `${i + 1}\n${srtTime(s.start)} --> ${srtTime(s.end)}\n${withSpeaker(s)}\n`).join("\n");
