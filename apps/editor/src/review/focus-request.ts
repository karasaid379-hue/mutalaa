import { useEffect, useRef, useState } from 'react';

/**
 * Moves focus to an element on request: `request()` after the state that renders the element (an error summary, a
 * heading, a button) was set. `attach` is a callback ref for the element, which needs `tabIndex={-1}` unless it is
 * focusable already. Focus moves once per request, and only when the element is there (it may mount in the same
 * render as the request).
 */
export function useFocusRequest<T extends HTMLElement>(): {
  attach: (element: T | null) => void;
  request: () => void;
} {
  const [element, setElement] = useState<T | null>(null);
  const [tick, setTick] = useState(0);
  const handled = useRef(0);
  useEffect(() => {
    if (tick > handled.current && element !== null) {
      handled.current = tick;
      element.focus();
    }
  }, [tick, element]);
  return { attach: setElement, request: () => setTick((value) => value + 1) };
}
