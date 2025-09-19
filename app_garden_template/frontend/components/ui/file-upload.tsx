'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone, DropzoneOptions } from 'react-dropzone';
import { Upload, X, AlertCircle, FileIcon } from 'lucide-react';

interface FileUploadProps {
  /**
   * Label displayed above the upload area
   */
  label: string;
  
  /**
   * Currently selected file
   */
  file: File | null;
  
  /**
   * Callback when a file is selected
   */
  onFileSelect: (file: File) => void;
  
  /**
   * Callback when the file is removed
   */
  onFileRemove: () => void;
  
  /**
   * Accepted file types (MIME types)
   */
  accept?: Record<string, string[]>;
  
  /**
   * Maximum file size in bytes
   */
  maxSize?: number;
  
  /**
   * Whether the component is disabled
   */
  disabled?: boolean;
  
  /**
   * Error message to display
   */
  error?: string;
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * File upload component with drag-and-drop support.
 * 
 * Features:
 * - Drag and drop file upload
 * - File type validation
 * - File size validation
 * - Progress indication
 * - Error handling
 * 
 * @example
 * ```tsx
 * <FileUpload
 *   label="Upload Document"
 *   file={selectedFile}
 *   onFileSelect={setSelectedFile}
 *   onFileRemove={() => setSelectedFile(null)}
 *   accept={{
 *     'application/pdf': ['.pdf'],
 *     'text/plain': ['.txt']
 *   }}
 *   maxSize={10 * 1024 * 1024} // 10MB
 * />
 * ```
 */
export function FileUpload({
  label,
  file,
  onFileSelect,
  onFileRemove,
  accept = {
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'text/markdown': ['.md'],
    'text/plain': ['.txt'],
    'text/csv': ['.csv'],
    'application/json': ['.json']
  },
  maxSize = 10 * 1024 * 1024, // 10MB default
  disabled = false,
  error,
  className = ''
}: FileUploadProps) {
  const [isDragReject, setIsDragReject] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setIsDragReject(false);
    
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const dropzoneOptions: DropzoneOptions = {
    onDrop,
    accept,
    maxFiles: 1,
    maxSize,
    disabled,
    onDropRejected: () => setIsDragReject(true)
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone(dropzoneOptions);

  return (
    <div className={`w-full ${className}`}>
      <label className="block text-sm font-medium mb-2">
        {label}
      </label>
      
      {!file ? (
        <div
          {...getRootProps()}
          className={`
            relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
            transition-all duration-200 ease-in-out
            ${isDragActive && !isDragReject ? 'border-primary bg-primary/5' : ''}
            ${isDragReject ? 'border-red-500 bg-red-500/5' : ''}
            ${!isDragActive && !isDragReject ? 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500' : ''}
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
            ${error ? 'border-red-500' : ''}
          `}
        >
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center">
            {isDragReject ? (
              <>
                <AlertCircle className="w-12 h-12 text-red-500 mb-3" />
                <p className="text-sm text-red-600 dark:text-red-400">
                  Invalid file type or size
                </p>
              </>
            ) : (
              <>
                <Upload className={`w-12 h-12 mb-3 ${isDragActive ? 'text-primary' : 'text-gray-400'}`} />
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  {isDragActive ? 'Drop the file here' : 'Drag and drop a file here, or click to select'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500">
                  Maximum file size: {formatFileSize(maxSize)}
                </p>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileIcon className="w-8 h-8 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {file.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatFileSize(file.size)}
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onFileRemove();
              }}
              className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              disabled={disabled}
            >
              <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            </button>
          </div>
        </div>
      )}
      
      {error && (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

/**
 * Format file size in human-readable format
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}