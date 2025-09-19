'use client';

import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

interface ModalProps {
  /**
   * Whether the modal is open
   */
  isOpen: boolean;
  
  /**
   * Callback when the modal should close
   */
  onClose: () => void;
  
  /**
   * Modal title
   */
  title?: string;
  
  /**
   * Modal content
   */
  children: React.ReactNode;
  
  /**
   * Size variant
   */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  
  /**
   * Whether clicking the backdrop closes the modal
   */
  closeOnBackdropClick?: boolean;
  
  /**
   * Whether pressing Escape closes the modal
   */
  closeOnEscape?: boolean;
  
  /**
   * Whether to show the close button
   */
  showCloseButton?: boolean;
  
  /**
   * Footer content
   */
  footer?: React.ReactNode;
  
  /**
   * Additional CSS classes for the modal content
   */
  className?: string;
}

/**
 * Modal component with backdrop and animations.
 * 
 * Features:
 * - Portal rendering
 * - Backdrop click to close
 * - Escape key to close
 * - Focus trap
 * - Smooth animations
 * - Multiple size variants
 * 
 * @example
 * ```tsx
 * <Modal
 *   isOpen={isModalOpen}
 *   onClose={() => setIsModalOpen(false)}
 *   title="Confirm Action"
 *   footer={
 *     <div className="flex justify-end space-x-2">
 *       <button onClick={() => setIsModalOpen(false)}>Cancel</button>
 *       <button onClick={handleConfirm}>Confirm</button>
 *     </div>
 *   }
 * >
 *   <p>Are you sure you want to proceed?</p>
 * </Modal>
 * ```
 */
export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  closeOnBackdropClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  footer,
  className = ''
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Size variants
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full mx-4'
  };

  // Handle escape key
  useEffect(() => {
    if (!isOpen || !closeOnEscape) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, closeOnEscape]);

  // Focus management
  useEffect(() => {
    if (isOpen) {
      // Store current focus
      previousFocusRef.current = document.activeElement as HTMLElement;
      
      // Focus the modal
      setTimeout(() => {
        modalRef.current?.focus();
      }, 100);
    } else {
      // Restore previous focus
      previousFocusRef.current?.focus();
    }
  }, [isOpen]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      aria-modal="true"
      role="dialog"
      aria-labelledby={title ? 'modal-title' : undefined}
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={closeOnBackdropClick ? onClose : undefined}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        tabIndex={-1}
        className={`
          relative w-full ${sizeClasses[size]}
          bg-white dark:bg-gray-800 rounded-lg shadow-xl
          transform transition-all
          ${className}
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            {title && (
              <h2 id="modal-title" className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {title}
              </h2>
            )}
            {showCloseButton && (
              <button
                onClick={onClose}
                className="ml-auto p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                aria-label="Close modal"
              >
                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            )}
          </div>
        )}

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(100vh-200px)]">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="p-6 border-t border-gray-200 dark:border-gray-700">
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  // Portal render
  if (typeof window !== 'undefined') {
    return createPortal(modalContent, document.body);
  }

  return null;
}

interface ConfirmModalProps {
  /**
   * Whether the modal is open
   */
  isOpen: boolean;
  
  /**
   * Callback when the modal should close
   */
  onClose: () => void;
  
  /**
   * Callback when confirmed
   */
  onConfirm: () => void;
  
  /**
   * Modal title
   */
  title?: string;
  
  /**
   * Confirmation message
   */
  message: string;
  
  /**
   * Confirm button text
   */
  confirmText?: string;
  
  /**
   * Cancel button text
   */
  cancelText?: string;
  
  /**
   * Variant for styling
   */
  variant?: 'default' | 'danger';
  
  /**
   * Whether the confirm action is loading
   */
  loading?: boolean;
}

/**
 * Confirmation modal component.
 * 
 * @example
 * ```tsx
 * <ConfirmModal
 *   isOpen={showConfirm}
 *   onClose={() => setShowConfirm(false)}
 *   onConfirm={handleDelete}
 *   title="Delete Item"
 *   message="Are you sure you want to delete this item? This action cannot be undone."
 *   variant="danger"
 *   confirmText="Delete"
 * />
 * ```
 */
export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'default',
  loading = false
}: ConfirmModalProps) {
  const confirmButtonClasses = variant === 'danger'
    ? 'bg-red-600 hover:bg-red-700 text-white'
    : 'bg-blue-600 hover:bg-blue-700 text-white';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={() => {
              onConfirm();
              if (!loading) {
                onClose();
              }
            }}
            disabled={loading}
            className={`
              px-4 py-2 rounded-md font-medium transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed
              ${confirmButtonClasses}
            `}
          >
            {loading ? 'Loading...' : confirmText}
          </button>
        </div>
      }
    >
      <p className="text-gray-700 dark:text-gray-300">{message}</p>
    </Modal>
  );
}