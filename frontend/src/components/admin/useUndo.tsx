"use client";

/**
 * Azione ottimistica con ANNULLA: l'UI cambia subito, la chiamata API parte
 * dopo 5s (o subito se arriva un'altra azione / si smonta la pagina).
 * Piu' veloce E piu' sicuro dei confirm() sugli swipe.
 *
 * Uso:
 *   const { perform, snackbar } = useUndo();
 *   perform({
 *     message: "Item eliminato",
 *     apply:  () => setItems(c => c.filter(...)),  // UI subito
 *     revert: () => setItems(prev),                // se ANNULLA
 *     commit: async () => adminApi.delete(...),    // dopo 5s
 *   });
 *   ...render... {snackbar}
 *
 * Una sola azione in sospeso alla volta: la successiva committa la
 * precedente immediatamente (niente code ambigue).
 */
import { useCallback, useEffect, useRef, useState } from "react";

interface UndoAction {
  message: string;
  apply: () => void;
  revert: () => void;
  commit: () => void | Promise<void>;
  /** Chiamata se il commit differito fallisce (es. rete giu'). */
  onCommitError?: (err: unknown) => void;
}

type PendingAction = Pick<UndoAction, "message" | "revert" | "commit" | "onCommitError">;

export function useUndo(timeoutMs = 5000) {
  const [pending, setPending] = useState<PendingAction | null>(null);
  const pendingRef = useRef<PendingAction | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const p = pendingRef.current;
    pendingRef.current = null;
    setPending(null);
    if (p) {
      Promise.resolve(p.commit()).catch((err) => p.onCommitError?.(err));
    }
  }, []);

  // Smontaggio pagina → committa subito (non perdere l'azione)
  useEffect(() => {
    return () => {
      const p = pendingRef.current;
      pendingRef.current = null;
      if (timerRef.current) clearTimeout(timerRef.current);
      if (p) {
        Promise.resolve(p.commit()).catch(() => {});
      }
    };
  }, []);

  const perform = useCallback(
    (action: UndoAction) => {
      flush(); // una alla volta: l'eventuale precedente parte ora
      action.apply();
      const p: PendingAction = {
        message: action.message,
        revert: action.revert,
        commit: action.commit,
        onCommitError: action.onCommitError,
      };
      pendingRef.current = p;
      setPending(p);
      timerRef.current = setTimeout(flush, timeoutMs);
    },
    [flush, timeoutMs],
  );

  const undo = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const p = pendingRef.current;
    pendingRef.current = null;
    setPending(null);
    p?.revert();
  }, []);

  const snackbar = pending ? (
    <div
      className="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-[60] bg-ink text-white rounded-full pl-5 pr-2 py-2 flex items-center gap-2 shadow-hover text-sm whitespace-nowrap"
      role="status"
    >
      <span>{pending.message}</span>
      <button
        type="button"
        onClick={undo}
        className="font-bold text-pink px-3 py-1.5 rounded-full hover:bg-white/10"
      >
        ANNULLA
      </button>
    </div>
  ) : null;

  return { perform, snackbar };
}
