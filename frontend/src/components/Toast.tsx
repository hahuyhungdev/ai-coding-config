import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

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
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5">
      {toasts.map(toast => (
        <div 
          key={toast.id} 
          className={`px-4.5 py-3 rounded-lg shadow-lg text-xs font-semibold font-display flex items-center gap-2 border animate-slide-up ${
            toast.type === 'success' ? 'bg-green/10 border-green/20 text-green' :
            toast.type === 'error' ? 'bg-red/10 border-red/20 text-red' :
            'bg-peach/10 border-peach/20 text-peach'
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
