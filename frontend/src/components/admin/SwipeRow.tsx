"use client";

import { useRef, useState } from "react";

/**
 * Wrapper swipe-to-action per righe di lista (mobile):
 *  - swipe verso DESTRA  → rivela il pannello verde a sinistra (rightAction)
 *  - swipe verso SINISTRA → rivela il pannello rosso a destra (leftAction)
 *
 * Solo touch: su desktop non interferisce (niente mouse events). Il gesto
 * si attiva solo quando l'intento orizzontale e' chiaro (dx > dy*1.5),
 * altrimenti lo scroll verticale della pagina resta fluido (touch-action:
 * pan-y). Dopo uno swipe il click "fantasma" sul contenuto (es. Link) viene
 * soppresso per non navigare per sbaglio.
 */
interface SwipeAction {
  label: string;
  icon: string;
  onTrigger: () => void;
}

interface Props {
  children: React.ReactNode;
  /** Azione dello swipe verso destra (pannello verde). */
  rightAction?: SwipeAction;
  /** Azione dello swipe verso sinistra (pannello rosso). */
  leftAction?: SwipeAction;
  /** Distanza in px per far scattare l'azione. */
  threshold?: number;
}

export function SwipeRow({
  children,
  rightAction,
  leftAction,
  threshold = 90,
}: Props) {
  const [dx, setDx] = useState(0);
  const [settling, setSettling] = useState(false);
  const start = useRef<{ x: number; y: number } | null>(null);
  const horizontal = useRef(false);
  const suppressClick = useRef(false);

  function onTouchStart(e: React.TouchEvent) {
    const t = e.touches[0];
    start.current = { x: t.clientX, y: t.clientY };
    horizontal.current = false;
    setSettling(false);
  }

  function onTouchMove(e: React.TouchEvent) {
    if (!start.current) return;
    const t = e.touches[0];
    const deltaX = t.clientX - start.current.x;
    const deltaY = t.clientY - start.current.y;

    if (!horizontal.current) {
      if (Math.abs(deltaX) > 12 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {
        horizontal.current = true;
      } else if (Math.abs(deltaY) > 12) {
        start.current = null; // scroll verticale: mollo il gesto
        return;
      } else {
        return; // intento non ancora chiaro
      }
    }

    let next = deltaX;
    if (next > 0 && !rightAction) next = 0;
    if (next < 0 && !leftAction) next = 0;
    // resistenza oltre la soglia (feel elastico)
    const max = threshold * 1.6;
    next = Math.max(-max, Math.min(max, next));
    setDx(next);
  }

  function onTouchEnd() {
    if (!start.current && dx === 0) return;
    start.current = null;
    if (Math.abs(dx) > 8) {
      suppressClick.current = true;
      setTimeout(() => (suppressClick.current = false), 350);
    }
    const fireRight = dx >= threshold && rightAction;
    const fireLeft = dx <= -threshold && leftAction;
    setSettling(true);
    setDx(0);
    if (fireRight) rightAction.onTrigger();
    else if (fireLeft) leftAction.onTrigger();
  }

  const progress = Math.min(1, Math.abs(dx) / threshold);

  return (
    <div
      className="relative overflow-hidden rounded-2xl"
      style={{ touchAction: "pan-y" }}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onTouchCancel={onTouchEnd}
      onClickCapture={(e) => {
        if (suppressClick.current) {
          e.preventDefault();
          e.stopPropagation();
        }
      }}
    >
      {/* Pannello sinistro (swipe → destra): verde */}
      {rightAction && dx > 0 && (
        <div
          className="absolute inset-y-0 left-0 right-0 flex items-center justify-start pl-5 rounded-2xl bg-mint-deep text-white font-bold text-sm gap-2"
          style={{ opacity: 0.35 + progress * 0.65 }}
          aria-hidden="true"
        >
          <span
            className="text-xl transition-transform"
            style={{ transform: `scale(${0.8 + progress * 0.5})` }}
          >
            {rightAction.icon}
          </span>
          <span>{rightAction.label}</span>
        </div>
      )}
      {/* Pannello destro (swipe → sinistra): rosso */}
      {leftAction && dx < 0 && (
        <div
          className="absolute inset-y-0 left-0 right-0 flex items-center justify-end pr-5 rounded-2xl bg-red-500 text-white font-bold text-sm gap-2"
          style={{ opacity: 0.35 + progress * 0.65 }}
          aria-hidden="true"
        >
          <span>{leftAction.label}</span>
          <span
            className="text-xl transition-transform"
            style={{ transform: `scale(${0.8 + progress * 0.5})` }}
          >
            {leftAction.icon}
          </span>
        </div>
      )}

      <div
        style={{
          transform: `translateX(${dx}px)`,
          transition: settling ? "transform 200ms ease" : "none",
        }}
      >
        {children}
      </div>
    </div>
  );
}
