'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/loading-spinner'
import { Button } from '@/components/ui/button'

interface LogEntry {
  timestamp: string
  level: string
  message: string
  details?: any
}

interface LogViewerProps {
  runId: string
  onClose: () => void
}

export function LogViewer({ runId, onClose }: LogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'info' | 'warning' | 'error'>('all')
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    loadLogs()
  }, [runId])

  const loadLogs = async () => {
    try {
      setIsLoading(true)
      const response = await api.get(`/rfp/runs/${runId}/logs`)
      setLogs(response.data.entries || [])
    } catch (error) {
      console.error('Failed to load logs:', error)
      setLogs([])
    } finally {
      setIsLoading(false)
    }
  }

  const filteredLogs = logs.filter(log => {
    if (filter === 'all') return true
    return log.level.toLowerCase() === filter
  })

  const getLogLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-500'
      case 'WARNING':
      case 'WARN':
        return 'text-yellow-500'
      case 'INFO':
        return 'text-blue-500'
      default:
        return 'text-gray-400'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-lg w-full max-w-6xl h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div>
            <h3 className="text-xl font-semibold text-white">Run Logs</h3>
            <p className="text-gray-400 text-sm mt-1">Run ID: {runId}</p>
          </div>
          <div className="flex items-center gap-4">
            {/* Log Level Filter */}
            <div className="flex gap-2">
              {(['all', 'info', 'warning', 'error'] as const).map((level) => (
                <Button
                  key={level}
                  size="sm"
                  variant={filter === level ? 'default' : 'outline'}
                  onClick={() => setFilter(level)}
                  className={
                    filter === level
                      ? 'bg-kamiwaza-green hover:bg-kamiwaza-green-dark'
                      : 'border-gray-600 text-gray-400 hover:text-white'
                  }
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </Button>
              ))}
            </div>

            {/* Auto-scroll Toggle */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setAutoScroll(!autoScroll)}
              className={autoScroll ? 'border-kamiwaza-blue text-kamiwaza-blue' : 'border-gray-600 text-gray-400'}
            >
              {autoScroll ? '⬇ Auto-scroll ON' : '⬇ Auto-scroll OFF'}
            </Button>

            {/* Close Button */}
            <Button
              size="sm"
              variant="ghost"
              onClick={onClose}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </Button>
          </div>
        </div>

        {/* Logs Content */}
        <div className="flex-1 overflow-auto p-4 font-mono text-sm">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="lg" />
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              No logs found for this run
            </div>
          ) : (
            <div className="space-y-1">
              {filteredLogs.map((log, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 py-1 hover:bg-gray-900 rounded px-2"
                >
                  {/* Timestamp */}
                  <span className="text-gray-500 text-xs whitespace-nowrap">
                    {formatTimestamp(log.timestamp)}
                  </span>

                  {/* Level */}
                  <span
                    className={`text-xs font-semibold uppercase w-16 text-right ${getLogLevelColor(
                      log.level
                    )}`}
                  >
                    {log.level}
                  </span>

                  {/* Message */}
                  <span className="text-gray-300 flex-1 break-all">
                    {log.message}
                  </span>

                  {/* Details (if any) */}
                  {log.details && (
                    <details className="text-gray-500">
                      <summary className="cursor-pointer text-xs">Details</summary>
                      <pre className="text-xs mt-1 p-2 bg-gray-900 rounded overflow-x-auto">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 flex items-center justify-between">
          <p className="text-gray-400 text-sm">
            Showing {filteredLogs.length} of {logs.length} log entries
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={loadLogs}
              className="border-gray-600 text-gray-400 hover:text-white"
            >
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={onClose}
              className="bg-gray-700 hover:bg-gray-600"
            >
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}