import React from 'react';
import { Notification } from '@mantine/core';

export interface ToastItem {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning';
}

interface ToastProps {
  toasts: ToastItem[];
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts }) => {
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2">
      {toasts.map(toast => {
        const color = toast.type === 'success' ? 'teal' : toast.type === 'error' ? 'red' : 'yellow';
        return (
          <Notification
            key={toast.id}
            color={color}
            withCloseButton={false}
            title={toast.type.toUpperCase()}
          >
            {toast.message}
          </Notification>
        );
      })}
    </div>
  );
};

