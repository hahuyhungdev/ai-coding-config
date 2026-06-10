import { useState, useCallback } from 'react';

export interface ToastItem {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning';
}

export function useToast(timeout = 4000) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, type: ToastItem['type'] = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, timeout);
  }, [timeout]);

  return { toasts, showToast };
}
