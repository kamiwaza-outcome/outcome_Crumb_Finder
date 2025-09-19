'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  /**
   * Child components to render
   */
  children: ReactNode;
  
  /**
   * Fallback UI to show when there's an error
   */
  fallback?: ReactNode;
  
  /**
   * Callback when an error is caught
   */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  
  /**
   * Whether to show the default error UI
   */
  showDefaultUI?: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error boundary component for graceful error handling.
 * 
 * Features:
 * - Catches JavaScript errors in child components
 * - Displays fallback UI
 * - Error reporting callback
 * - Reset functionality
 * 
 * @example
 * ```tsx
 * <ErrorBoundary
 *   onError={(error, errorInfo) => {
 *     // Log to error reporting service
 *     console.error('Error caught:', error, errorInfo);
 *   }}
 * >
 *   <App />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // Update state with error info
    this.setState({
      errorInfo
    });

    // Call the error callback if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return <>{this.props.fallback}</>;
      }

      // Default error UI
      if (this.props.showDefaultUI !== false) {
        return <DefaultErrorUI error={this.state.error} onReset={this.handleReset} />;
      }

      // Minimal fallback
      return null;
    }

    return this.props.children;
  }
}

interface DefaultErrorUIProps {
  error: Error | null;
  onReset: () => void;
}

function DefaultErrorUI({ error, onReset }: DefaultErrorUIProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6">
          <div className="flex items-center space-x-3 mb-4">
            <AlertTriangle className="w-8 h-8 text-red-500" />
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Something went wrong
            </h1>
          </div>
          
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            We&apos;re sorry, but something unexpected happened. Please try refreshing the page.
          </p>

          {process.env.NODE_ENV === 'development' && error && (
            <details className="mb-4">
              <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                Error details (development only)
              </summary>
              <pre className="mt-2 p-3 bg-gray-100 dark:bg-gray-900 rounded text-xs overflow-auto">
                {error.toString()}
                {error.stack && '\n\n' + error.stack}
              </pre>
            </details>
          )}

          <div className="flex space-x-3">
            <button
              onClick={onReset}
              className="flex-1 flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </button>
            <button
              onClick={() => window.location.href = '/'}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              Go Home
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Higher-order component to wrap a component with error boundary.
 * 
 * @example
 * ```tsx
 * const SafeComponent = withErrorBoundary(MyComponent, {
 *   fallback: <div>Error loading component</div>,
 *   onError: (error) => console.error(error)
 * });
 * ```
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
): React.ComponentType<P> {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}