"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "cn";
import { CARDS, EDGES, LANES, PHASES, type LaneId, type RoadmapCard } from "../data";

/**
 * Bảng lộ trình: hàng = giai đoạn, cột = làn (Quản trị · Con người · Công cụ). Mũi tên SVG vẽ theo vị trí thật của
 * thẻ nên phải đo DOM sau khi render và đo lại khi khung đổi kích thước. Dưới 1081px không vẽ mũi tên: các thẻ xếp
 * dọc theo giai đoạn và mối liên hệ hiện thành nút bấm trong từng thẻ.
 */

type Filter = "all" | "original" | "added";

/** Màu từng làn: [chữ/tiêu đề, nền cột, nền thẻ, viền thẻ]. */
const LANE_STYLE: Record<LaneId, CSSProperties> = {
  gov: { "--lane": "#1e3a8a", "--lane-tint": "#f5f7fd", "--lane-card": "#e7edfa", "--lane-line": "#b7c5e8" } as CSSProperties,
  people: { "--lane": "#0369a1", "--lane-tint": "#f3f9fe", "--lane-card": "#e1f1fc", "--lane-line": "#a6d0ec" } as CSSProperties,
  tools: { "--lane": "#0f766e", "--lane-tint": "#f2faf9", "--lane-card": "#dff3ef", "--lane-line": "#a3d7cd" } as CSSProperties,
};

const WIDE_QUERY = "(min-width: 1081px)";

interface Wire {
  d: string;
  f: string;
  t: string;
  main: boolean;
  ret: boolean;
}
interface WireLabel {
  x: number;
  y: number;
  text: string;
  rot: boolean;
  f: string;
  t: string;
}
interface Geometry {
  w: number;
  h: number;
  gates: { y: number; x1: number; x2: number }[];
  wires: Wire[];
  labels: WireLabel[];
}

interface Box {
  l: number;
  r: number;
  t: number;
  b: number;
  cx: number;
  cy: number;
  w: number;
}

function measure(board: HTMLElement, el: Element): Box {
  const b = board.getBoundingClientRect();
  const r = el.getBoundingClientRect();
  const l = r.left - b.left;
  const rr = r.right - b.left;
  const t = r.top - b.top;
  const bb = r.bottom - b.top;
  return { l, r: rr, t, b: bb, cx: (l + rr) / 2, cy: (t + bb) / 2, w: rr - l };
}

/** Đo DOM rồi dựng đường đi cho mọi mũi tên. Logic hình học giữ nguyên bản HTML gốc. */
function computeGeometry(board: HTMLElement, cards: Map<string, HTMLElement>): Geometry | null {
  const bandEls = Array.from(board.querySelectorAll<HTMLElement>("[data-band]"));
  if (bandEls.length !== 3 || cards.size === 0) return null;
  const bands = bandEls.map((el) => measure(board, el));
  const colL = bands.map((b) => b.l + 12);
  const colR = bands.map((b) => b.r - 12);
  const rowGap = parseFloat(getComputedStyle(board).rowGap) || 68;

  const gates = Array.from(board.querySelectorAll<HTMLElement>("[data-gate]")).map((p) => ({
    y: measure(board, p).b + 8,
    x1: bands[0].l,
    x2: bands[2].r,
  }));

  const wires: Wire[] = [];
  const labels: WireLabel[] = [];
  const laneOf = (card: HTMLElement) => Number(card.closest<HTMLElement>("[data-cell]")?.dataset.lane ?? 0);

  for (const e of EDGES) {
    const sc = cards.get(e.f);
    const tc = cards.get(e.t);
    if (!sc || !tc) continue;
    const s = measure(board, sc);
    const t = measure(board, tc);
    const sx = s.l + s.w * (e.sa ?? 0.5);
    const tx = t.l + t.w * (e.ta ?? 0.5);
    const sameCell = sc.closest("[data-cell]") === tc.closest("[data-cell]");
    const cellTop = measure(board, tc.closest("[data-cell]")!).t;
    const my = cellTop - rowGap / 2 + (e.o ?? 0);
    let lf = e.lf ?? 0.5;
    let seg = 0;
    let rot = false;
    let pts: [number, number][] = [];

    if (e.r === "down") {
      if (sameCell || Math.abs(sx - tx) < 1) {
        pts = [[sx, s.b], [sx, t.t]];
      } else {
        pts = [[sx, s.b], [sx, my], [tx, my], [tx, t.t]];
        seg = 1;
      }
    } else if (e.r === "gutter") {
      const lt = laneOf(tc);
      const gxm = (colR[lt - 1] + colL[lt]) / 2 + (e.gx ?? 0);
      pts = [[sx, s.b], [sx, my], [gxm, my], [gxm, t.cy], [t.l, t.cy]];
      seg = 2;
    } else if (e.r === "side") {
      const ls = laneOf(sc);
      const ltt = laneOf(tc);
      const right = ltt > ls;
      const a = right ? ls : ltt;
      const gx = (colR[a] + colL[a + 1]) / 2 + (e.gx ?? 0);
      pts = [[right ? s.r : s.l, s.cy], [gx, s.cy], [gx, t.cy], [right ? t.l : t.r, t.cy]];
      seg = Math.abs(t.cy - s.cy) > 40 ? 1 : 0;
      if (seg === 0) lf = 0.5;
    } else if (e.r === "right") {
      const rx = bands[2].r + 14;
      pts = [[s.r, s.cy], [rx, s.cy], [rx, my], [tx, my], [tx, t.t]];
      seg = 3;
      lf = 0.35;
    } else {
      const lx = bands[0].l - 14;
      pts = [[s.l, s.cy], [lx, s.cy], [lx, t.cy], [t.l, t.cy]];
      seg = 1;
      rot = true;
    }

    wires.push({
      d: "M" + pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" L"),
      f: e.f,
      t: e.t,
      main: !!e.main,
      ret: !!e.ret,
    });
    if (e.l) {
      const p0 = pts[seg];
      const p1 = pts[seg + 1];
      labels.push({ x: p0[0] + (p1[0] - p0[0]) * lf, y: p0[1] + (p1[1] - p0[1]) * lf, text: e.l, rot, f: e.f, t: e.t });
    }
  }
  return { w: board.scrollWidth, h: board.scrollHeight, gates, wires, labels };
}

export function RoadmapBoard() {
  const boardRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const [filter, setFilter] = useState<Filter>("all");
  const [current, setCurrent] = useState<string | null>(null);
  const [geo, setGeo] = useState<Geometry | null>(null);

  const linked = useMemo(() => {
    const set = new Set<string>();
    if (!current) return set;
    for (const e of EDGES) {
      if (e.f === current) set.add(e.t);
      if (e.t === current) set.add(e.f);
    }
    return set;
  }, [current]);

  const focus = useCallback((id: string) => setCurrent((cur) => (cur === id ? null : id)), []);

  const redraw = useCallback(() => {
    const board = boardRef.current;
    if (!board || !window.matchMedia(WIDE_QUERY).matches) {
      setGeo(null);
      return;
    }
    setGeo(computeGeometry(board, cardRefs.current));
  }, []);

  useLayoutEffect(() => {
    const board = boardRef.current;
    if (!board) return;
    let raf = 0;
    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(redraw);
    };
    const ro = new ResizeObserver(schedule);
    ro.observe(board);
    const mq = window.matchMedia(WIDE_QUERY);
    mq.addEventListener("change", schedule);
    window.addEventListener("resize", schedule);
    // Font tải xong làm đổi chiều cao thẻ, nên phải đo lại.
    void document.fonts?.ready.then(schedule);
    redraw();
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      mq.removeEventListener("change", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [redraw]);

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") setCurrent(null);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const focusing = current !== null;
  const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const cardsOf = (phase: number, lane: LaneId) => CARDS.filter((c) => c.phase === phase && c.lane === lane);

  const dimmed = (c: RoadmapCard) =>
    (focusing && c.id !== current && !linked.has(c.id)) ||
    (filter === "added" && !c.added) ||
    (filter === "original" && !!c.added);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-7 gap-y-3">
        <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-2 text-[13px]" aria-label="Chú giải">
          {LANES.map((l) => (
            <span key={l.id} className="inline-flex items-center gap-2" style={LANE_STYLE[l.id]}>
              <i className="inline-block size-3 rounded-[3px] bg-[var(--lane)]" />
              {l.legend}
            </span>
          ))}
          <span className="inline-flex items-center gap-2">
            <i className="border-muted-foreground inline-block size-3 rounded-[3px] border-[1.5px] border-dashed" />
            Ý bổ sung
          </span>
          <span className="inline-flex items-center gap-2">
            <i className="border-destructive inline-block h-0 w-[18px] border-t-2 border-dashed" />
            Cổng duyệt
          </span>
        </div>
        <ToggleGroup
          type="single"
          variant="outline"
          size="sm"
          spacing={0}
          value={filter}
          onValueChange={(v) => v && setFilter(v as Filter)}
          aria-label="Lọc thẻ"
        >
          <ToggleGroupItem value="all">Tất cả</ToggleGroupItem>
          <ToggleGroupItem value="original">Kế hoạch gốc</ToggleGroupItem>
          <ToggleGroupItem value="added">Ý bổ sung</ToggleGroupItem>
        </ToggleGroup>
        <span className="text-muted-foreground text-[13px]">Bấm một thẻ để làm nổi các mũi tên của nó. Esc để bỏ chọn.</span>
      </div>

      <div className="bg-card rounded-2xl border pt-5 pb-7 max-[1080px]:border-0 max-[1080px]:bg-transparent max-[1080px]:p-0">
        <div
          ref={boardRef}
          className={cn(
            "relative grid pl-5 [row-gap:68px]",
            "grid-cols-[150px_44px_minmax(0,1fr)_96px_minmax(0,1fr)_96px_minmax(0,1fr)_40px]",
            "max-[1080px]:flex max-[1080px]:flex-col max-[1080px]:gap-3 max-[1080px]:pl-0",
          )}
          style={{ "--edge": "#9aa8bd" } as CSSProperties}
        >
          {/* Nền ba làn */}
          {LANES.map((l, i) => (
            <div
              key={l.id}
              data-band={l.id}
              style={{ ...LANE_STYLE[l.id], gridRow: "1 / -1", gridColumn: 3 + i * 2 }}
              className="z-0 -mx-3 -mt-2.5 -mb-3.5 rounded-xl bg-[var(--lane-tint)] max-[1080px]:hidden"
            />
          ))}
          {LANES.map((l, i) => (
            <div
              key={l.id}
              style={{ ...LANE_STYLE[l.id], gridRow: 1, gridColumn: 3 + i * 2 }}
              className="z-[2] flex flex-col gap-0.5 text-xs font-bold tracking-wider text-[var(--lane)] uppercase max-[1080px]:hidden"
            >
              {l.title}
              <small className="text-muted-foreground text-[11.5px] font-medium tracking-normal normal-case">{l.owner}</small>
            </div>
          ))}

          {PHASES.map((p) => (
            <PhaseRow key={p.n} phase={p}>
              {LANES.map((l, li) => (
                <div
                  key={l.id}
                  data-cell
                  data-lane={li}
                  style={{ ...LANE_STYLE[l.id], gridRow: p.n + 1, gridColumn: 3 + li * 2 }}
                  className={cn(
                    "z-[2] flex min-w-0 flex-col gap-[34px]",
                    "max-[1080px]:bg-card max-[1080px]:gap-2.5 max-[1080px]:rounded-xl max-[1080px]:border max-[1080px]:p-3",
                    cardsOf(p.n, l.id).length === 0 && "max-[1080px]:hidden",
                  )}
                >
                  <span className="hidden text-[11px] font-bold tracking-wider text-[var(--lane)] uppercase max-[1080px]:block">
                    {l.title}
                  </span>
                  {cardsOf(p.n, l.id).map((c) => (
                    <RoadmapCardView
                      key={c.id}
                      card={c}
                      dim={dimmed(c)}
                      isFocus={c.id === current}
                      isLinked={linked.has(c.id)}
                      onFocus={focus}
                      onJump={(id) => {
                        focus(id);
                        cardRefs.current.get(id)?.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth", block: "center" });
                      }}
                      register={(el) => {
                        if (el) cardRefs.current.set(c.id, el);
                        else cardRefs.current.delete(c.id);
                      }}
                    />
                  ))}
                </div>
              ))}
            </PhaseRow>
          ))}

          {geo && (
            <>
              <svg
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 z-[1] size-full overflow-visible max-[1080px]:hidden"
                viewBox={`0 0 ${geo.w} ${geo.h}`}
              >
                <defs>
                  <marker id="rm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M0,0 L10,5 L0,10 z" fill="var(--edge)" />
                  </marker>
                  <marker id="rm-ah-ink" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M0,0 L10,5 L0,10 z" fill="var(--primary)" />
                  </marker>
                </defs>
                {geo.gates.map((g, i) => (
                  <line
                    key={i}
                    x1={g.x1}
                    x2={g.x2}
                    y1={g.y}
                    y2={g.y}
                    stroke="var(--destructive)"
                    strokeWidth={1.5}
                    strokeDasharray="6 5"
                    opacity={0.75}
                  />
                ))}
                {geo.wires.map((w, i) => {
                  const hi = focusing && (w.f === current || w.t === current);
                  return (
                    <path
                      key={i}
                      d={w.d}
                      fill="none"
                      strokeLinejoin="round"
                      stroke={hi || w.main ? "var(--primary)" : "var(--edge)"}
                      strokeWidth={hi ? 2.6 : w.main ? 2 : 1.6}
                      strokeDasharray={w.ret ? "5 4" : undefined}
                      markerEnd={hi || w.main ? "url(#rm-ah-ink)" : "url(#rm-ah)"}
                      className="transition-[opacity,stroke] duration-200 motion-reduce:transition-none"
                      opacity={focusing && !hi ? 0.15 : 1}
                    />
                  );
                })}
              </svg>
              <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-[3] max-[1080px]:hidden">
                {geo.labels.map((lb, i) => {
                  const hi = focusing && (lb.f === current || lb.t === current);
                  return (
                    <span
                      key={i}
                      style={{ left: lb.x, top: lb.y, opacity: focusing && !hi ? 0.15 : 1 }}
                      className={cn(
                        "bg-card absolute -translate-x-1/2 -translate-y-1/2 rounded-md border px-1.5 py-0.5 text-center text-[11px] leading-tight font-semibold transition-opacity duration-200 motion-reduce:transition-none",
                        lb.rot ? "-rotate-90 whitespace-nowrap" : "max-w-[88px]",
                      )}
                    >
                      {lb.text}
                    </span>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/** Ô giai đoạn ở cột trái, kèm ba ô làn (children) cùng hàng lưới. */
function PhaseRow({ phase, children }: { phase: (typeof PHASES)[number]; children: React.ReactNode }) {
  return (
    <>
      <div
        data-gate={phase.gate?.code}
        style={{ gridRow: phase.n + 1, gridColumn: 1 }}
        className="z-[2] flex flex-col gap-1 pt-0.5 max-[1080px]:pt-[22px]"
      >
        <span className="text-muted-foreground font-mono text-xs font-semibold">GĐ {phase.n}</span>
        <h2 className="text-[17px] leading-snug font-bold">{phase.title}</h2>
        <span className="text-muted-foreground text-[12.5px] tabular-nums">{phase.time}</span>
        {phase.gate && (
          <span className="text-destructive mt-auto flex items-baseline gap-[7px] pt-3.5 text-xs leading-snug font-semibold max-[1080px]:mt-1 max-[1080px]:pt-0">
            <i className="size-2 shrink-0 -translate-y-px rotate-45 bg-current" />
            Cổng {phase.gate.code}: {phase.gate.text}
          </span>
        )}
      </div>
      {children}
    </>
  );
}

function RoadmapCardView({
  card,
  dim,
  isFocus,
  isLinked,
  onFocus,
  onJump,
  register,
}: {
  card: RoadmapCard;
  dim: boolean;
  isFocus: boolean;
  isLinked: boolean;
  onFocus: (id: string) => void;
  onJump: (id: string) => void;
  register: (el: HTMLElement | null) => void;
}) {
  const related = EDGES.flatMap((e) => {
    if (e.f === card.id) return [{ id: e.t, dir: "→", label: e.l }];
    if (e.t === card.id) return [{ id: e.f, dir: "←", label: e.l }];
    return [];
  });

  return (
    <Card
      ref={register}
      role="button"
      tabIndex={0}
      aria-pressed={isFocus}
      data-id={card.id}
      onClick={() => onFocus(card.id)}
      onKeyDown={(ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          onFocus(card.id);
        }
      }}
      className={cn(
        "min-w-0 cursor-pointer gap-[7px] rounded-[9px] border bg-[var(--lane-card)] px-[13px] py-[11px] shadow-sm transition-[opacity,box-shadow,border-color] duration-200 outline-none motion-reduce:transition-none",
        "border-[var(--lane-line)] focus-visible:ring-2 focus-visible:ring-foreground focus-visible:ring-offset-2",
        card.added && "border-[1.5px] border-dashed",
        (isFocus || isLinked) && "border-foreground border-solid",
        isFocus && "ring-foreground ring-2",
        dim && "opacity-25",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="rounded-[5px] bg-[var(--lane)] px-[7px] font-mono text-xs font-semibold text-white">{card.id}</Badge>
        {card.added && <span className="text-muted-foreground text-[10.5px] font-semibold tracking-wide uppercase">Bổ sung</span>}
        {card.early && <span className="text-destructive text-[10.5px] font-semibold">{card.early}</span>}
      </div>
      <h3 className="text-sm leading-snug font-bold">{card.title}</h3>
      <ul className="text-muted-foreground flex list-disc flex-col gap-[3px] pl-4 text-[13px] marker:text-[var(--edge)]">
        {card.bullets.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>
      {card.now && <p className="bg-card rounded-md px-2 py-1.5 text-xs">{card.now}</p>}
      <div className="flex flex-wrap gap-[5px] pt-0.5 min-[1081px]:hidden">
        {related.map((r) => (
          <Button
            key={`${r.dir}${r.id}`}
            type="button"
            variant="outline"
            size="xs"
            className="text-muted-foreground h-6 rounded-full px-2.5 text-[11.5px] font-normal"
            onClick={(ev) => {
              ev.stopPropagation();
              onJump(r.id);
            }}
          >
            {r.dir} <b className="text-foreground font-mono font-semibold">{r.id}</b>
            {r.label ? ` · ${r.label}` : ""}
          </Button>
        ))}
      </div>
    </Card>
  );
}
