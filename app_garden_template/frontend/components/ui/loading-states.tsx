'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

interface SpinnerProps {
  /**
   * Size of the spinner
   */
  size?: 'sm' | 'md' | 'lg';
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Simple loading spinner component.
 * 
 * @example
 * ```tsx
 * <Spinner size="lg" />
 * ```
 */
export function Spinner({ size = 'md', className = '' }: SpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  return (
    <Loader2 
      className={`animate-spin ${sizeClasses[size]} ${className}`}
      aria-label="Loading"
    />
  );
}

interface LoadingOverlayProps {
  /**
   * Loading message to display
   */
  message?: string;
  
  /**
   * Whether to show a backdrop
   */
  backdrop?: boolean;
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Full-screen loading overlay.
 * 
 * @example
 * ```tsx
 * {isLoading && <LoadingOverlay message="Processing..." />}
 * ```
 */
export function LoadingOverlay({ 
  message = 'Loading...', 
  backdrop = true,
  className = '' 
}: LoadingOverlayProps) {
  return (
    <div 
      className={`
        fixed inset-0 z-50 flex items-center justify-center
        ${backdrop ? 'bg-black/50' : ''}
        ${className}
      `}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-xl">
        <div className="flex flex-col items-center space-y-4">
          <Spinner size="lg" />
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {message}
          </p>
        </div>
      </div>
    </div>
  );
}

interface SkeletonProps {
  /**
   * Width of the skeleton (CSS value)
   */
  width?: string;
  
  /**
   * Height of the skeleton (CSS value)
   */
  height?: string;
  
  /**
   * Shape variant
   */
  variant?: 'text' | 'rect' | 'circle';
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Skeleton loader for content placeholders.
 * 
 * @example
 * ```tsx
 * <Skeleton width="200px" height="20px" variant="text" />
 * ```
 */
export function Skeleton({ 
  width = '100%', 
  height = '20px', 
  variant = 'rect',
  className = '' 
}: SkeletonProps) {
  const variantClasses = {
    text: 'rounded',
    rect: 'rounded-md',
    circle: 'rounded-full'
  };

  return (
    <div
      className={`
        animate-pulse bg-gray-200 dark:bg-gray-700
        ${variantClasses[variant]}
        ${className}
      `}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

interface CardSkeletonProps {
  /**
   * Number of lines to show
   */
  lines?: number;
  
  /**
   * Whether to show an avatar
   */
  showAvatar?: boolean;
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Card skeleton loader.
 * 
 * @example
 * ```tsx
 * <CardSkeleton lines={3} showAvatar />
 * ```
 */
export function CardSkeleton({ 
  lines = 3, 
  showAvatar = false,
  className = '' 
}: CardSkeletonProps) {
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow ${className}`}>
      <div className="flex items-start space-x-4">
        {showAvatar && (
          <Skeleton width="48px" height="48px" variant="circle" />
        )}
        <div className="flex-1 space-y-3">
          <Skeleton width="60%" height="24px" />
          {Array.from({ length: lines }).map((_, i) => (
            <Skeleton 
              key={i} 
              width={i === lines - 1 ? "80%" : "100%"} 
              height="16px" 
            />
          ))}
        </div>
      </div>
    </div>
  );
}

interface LoadingButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * Whether the button is in loading state
   */
  loading?: boolean;
  
  /**
   * Loading text to display
   */
  loadingText?: string;
  
  /**
   * Button content
   */
  children: React.ReactNode;
}

/**
 * Button with loading state.
 * 
 * @example
 * ```tsx
 * <LoadingButton loading={isSubmitting} loadingText="Saving...">
 *   Save Changes
 * </LoadingButton>
 * ```
 */
export function LoadingButton({ 
  loading = false, 
  loadingText = 'Loading...',
  children,
  disabled,
  className = '',
  ...props 
}: LoadingButtonProps) {
  return (
    <button
      disabled={loading || disabled}
      className={`
        relative inline-flex items-center justify-center
        px-4 py-2 rounded-md font-medium
        transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
      {...props}
    >
      {loading && (
        <Spinner size="sm" className="absolute left-3" />
      )}
      <span className={loading ? 'opacity-0' : ''}>
        {children}
      </span>
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          {loadingText}
        </span>
      )}
    </button>
  );
}

interface ProgressBarProps {
  /**
   * Progress value (0-100)
   */
  value: number;
  
  /**
   * Whether to show the percentage text
   */
  showLabel?: boolean;
  
  /**
   * Height of the progress bar
   */
  height?: 'sm' | 'md' | 'lg';
  
  /**
   * Color variant
   */
  variant?: 'primary' | 'success' | 'warning' | 'error';
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Progress bar component.
 * 
 * @example
 * ```tsx
 * <ProgressBar value={75} showLabel variant="primary" />
 * ```
 */
export function ProgressBar({ 
  value, 
  showLabel = false,
  height = 'md',
  variant = 'primary',
  className = '' 
}: ProgressBarProps) {
  const heightClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-4'
  };

  const variantClasses = {
    primary: 'bg-blue-600',
    success: 'bg-green-600',
    warning: 'bg-yellow-600',
    error: 'bg-red-600'
  };

  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={`w-full ${className}`}>
      <div className={`
        relative w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden
        ${heightClasses[height]}
      `}>
        <div
          className={`
            h-full transition-all duration-300 ease-out
            ${variantClasses[variant]}
          `}
          style={{ width: `${clampedValue}%` }}
          role="progressbar"
          aria-valuenow={clampedValue}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {showLabel && (
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 text-center">
          {clampedValue}%
        </p>
      )}
    </div>
  );
}