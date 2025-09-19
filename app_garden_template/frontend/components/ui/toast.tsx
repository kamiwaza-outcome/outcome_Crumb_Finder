'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { createPortal } from 'react-dom';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

/**
 * Toast provider component.
 * Wrap your app with this provider to enable toast notifications.
 * 
 * @example
 * ```tsx
 * // In your root layout or _app.tsx
 * <ToastProvider>
 *   <App />
 * </ToastProvider>
 * ```
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(7);
    const newToast = { ...toast, id };
    
    setToasts((prev) => [...prev, newToast]);

    // Auto-remove after duration
    if (toast.duration !== 0) {
      setTimeout(() => {
        removeToast(id);
      }, toast.duration || 5000);
    }
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
}

/**
 * Hook to use toast notifications.
 * 
 * @example
 * ```tsx
 * const { showToast } = useToast();
 * 
 * // Show a success toast
 * showToast({
 *   type: 'success',
 *   title: 'Settings saved',
 *   message: 'Your changes have been saved successfully.'
 * });
 * ```
 */
export function useToast() {
  const context = useContext(ToastContext);
  
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }

  const showToast = useCallback((toast: Omit<Toast, 'id'>) => {
    context.addToast(toast);
  }, [context]);

  return {
    showToast,
    toasts: context.toasts,
    removeToast: context.removeToast
  };
}

function ToastContainer() {
  const context = useContext(ToastContext);
  
  if (!context || context.toasts.length === 0) {
    return null;
  }

  const content = (
    <div className="fixed bottom-4 right-4 z-50 space-y-4 max-w-sm">
      {context.toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onClose={() => context.removeToast(toast.id)}
        />
      ))}
    </div>
  );

  if (typeof window !== 'undefined') {
    return createPortal(content, document.body);
  }

  return null;
}

interface ToastItemProps {
  toast: Toast;
  onClose: () => void;
}

function ToastItem({ toast, onClose }: ToastItemProps) {
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-500" />,
    error: <AlertCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />
  };

  const bgColors = {
    success: 'bg-green-50 dark:bg-green-900/20',
    error: 'bg-red-50 dark:bg-red-900/20',
    warning: 'bg-yellow-50 dark:bg-yellow-900/20',
    info: 'bg-blue-50 dark:bg-blue-900/20'
  };

  return (
    <div
      className={`
        flex items-start p-4 rounded-lg shadow-lg
        bg-white dark:bg-gray-800 border
        transform transition-all duration-300 ease-out
        animate-slide-in-right
        ${bgColors[toast.type]}
      `}
      role="alert"
    >
      <div className="flex-shrink-0">
        {icons[toast.type]}
      </div>
      
      <div className="ml-3 flex-1">
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {toast.title}
        </h3>
        {toast.message && (
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {toast.message}
          </p>
        )}
      </div>
      
      <button
        onClick={onClose}
        className="ml-4 flex-shrink-0 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        aria-label="Close notification"
      >
        <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
      </button>
    </div>
  );
}

// Add animation to global CSS
const style = `
@keyframes slide-in-right {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.animate-slide-in-right {
  animation: slide-in-right 0.3s ease-out;
}
`;

if (typeof window !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = style;
  document.head.appendChild(styleElement);
}

// Simple toast helper for use without context
export const toast = {
  success: (message: string) => {
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('toast', {
        detail: { type: 'success', title: message }
      });
      window.dispatchEvent(event);
    }
  },
  error: (message: string) => {
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('toast', {
        detail: { type: 'error', title: message }
      });
      window.dispatchEvent(event);
    }
  },
  info: (message: string) => {
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('toast', {
        detail: { type: 'info', title: message }
      });
      window.dispatchEvent(event);
    }
  }
}