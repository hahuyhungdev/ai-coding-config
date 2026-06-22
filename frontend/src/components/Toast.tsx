import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface ToastItem {
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
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`glass px-4 py-3 rounded-lg shadow-2xl text-[12px] font-medium flex items-center gap-2.5 animate-slide-in ${
            toast.type === 'success' ? 'border-success/20 text-success' :
            toast.type === 'error' ? 'border-error/20 text-error' :
            'border-warning/20 text-warning'
          }`}
        >
          {toast.type === 'success' && <CheckCircle2 className="h-4 w-4" />}
          {toast.type === 'error' && <XCircle className="h-4 w-4" />}
          {toast.type === 'warning' && <AlertTriangle className="h-4 w-4" />}
          {toast.message}
        </div>
      ))}
    </div>
  );
};
