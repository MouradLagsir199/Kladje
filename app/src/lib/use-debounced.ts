import { useCallback, useEffect, useRef } from "react";

/**
 * Call `fn` at most once per `delayMs`, on the trailing edge, and never after unmount.
 *
 * Used by the review screen so typing a title is one PATCH rather than one per keystroke. `flush`
 * exists for the moment before navigating away: a debounced edit that is still pending when the
 * screen closes would be silently lost, which is the worst possible outcome for a correction
 * someone just made by hand.
 */
export function useDebounced<A extends unknown[]>(
  fn: (...args: A) => void,
  delayMs = 600,
): { call: (...args: A) => void; flush: () => void } {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pending = useRef<A | null>(null);
  const latest = useRef(fn);

  // Kept in a ref so a re-render with a new closure does not restart the timer.
  useEffect(() => {
    latest.current = fn;
  }, [fn]);

  const run = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const args = pending.current;
    pending.current = null;
    if (args) latest.current(...args);
  }, []);

  const call = useCallback(
    (...args: A) => {
      pending.current = args;
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(run, delayMs);
    },
    [delayMs, run],
  );

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  return { call, flush: run };
}
