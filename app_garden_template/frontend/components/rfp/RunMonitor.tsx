'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/loading-spinner'

interface RunProgress {
  found: number
  processed: number
  qualified: number
  maybe: number
  rejected: number
  errors: number
}

interface DiscoveryRun {
  run_id: string
  status: string
  started_at: string
  total_found: number
  total_processed: number
  total_qualified: number
  total_maybe: number
  total_rejected: number
  total_errors: number
  search_config: {
    model_name: string
    batch_size: number
    max_rfps: number
  }
}

interface RunMonitorProps {
  run: DiscoveryRun
}

export function RunMonitor({ run }: RunMonitorProps) {
  const [progress, setProgress] = useState<RunProgress>({
    found: run.total_found,
    processed: run.total_processed,
    qualified: run.total_qualified,
    maybe: run.total_maybe,
    rejected: run.total_rejected,
    errors: run.total_errors
  })

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.host
    const ws = new WebSocket(`${wsProtocol}//${wsHost}/api/rfp/ws/run/${run.run_id}`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.progress) {
        setProgress(data.progress)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    return () => {
      ws.close()
    }
  }, [run.run_id])

  const progressPercentage = progress.found > 0
    ? Math.round((progress.processed / progress.found) * 100)
    : 0

  return (
    <Card className="bg-gray-800 border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">
          Active Discovery Run
        </h2>
        <div className="flex items-center gap-2">
          <LoadingSpinner size="sm" />
          <span className="text-kamiwaza-green font-medium">RUNNING</span>
        </div>
      </div>

      <div className="space-y-4">
        {/* Run Details */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-gray-400">Run ID</p>
            <p className="text-white font-mono">{run.run_id}</p>
          </div>
          <div>
            <p className="text-gray-400">Model</p>
            <p className="text-white">{run.search_config.model_name}</p>
          </div>
          <div>
            <p className="text-gray-400">Batch Size</p>
            <p className="text-white">{run.search_config.batch_size}</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-400">Progress</span>
            <span className="text-white">
              {progress.processed} / {progress.found} RFPs
            </span>
          </div>
          <div className="w-full bg-gray-900 rounded-full h-2">
            <div
              className="bg-gradient-to-r from-kamiwaza-green to-kamiwaza-blue h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          <p className="text-center text-gray-400 text-sm mt-1">
            {progressPercentage}% Complete
          </p>
        </div>

        {/* Statistics Grid */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-gray-900 rounded-lg p-3">
            <p className="text-gray-400 text-xs mb-1">Found</p>
            <p className="text-2xl font-bold text-white">{progress.found}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-3">
            <p className="text-gray-400 text-xs mb-1">Qualified</p>
            <p className="text-2xl font-bold text-green-500">{progress.qualified}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-3">
            <p className="text-gray-400 text-xs mb-1">Maybe</p>
            <p className="text-2xl font-bold text-yellow-500">{progress.maybe}</p>
          </div>
          <div className="bg-gray-900 rounded-lg p-3">
            <p className="text-gray-400 text-xs mb-1">Rejected</p>
            <p className="text-2xl font-bold text-red-500">{progress.rejected}</p>
          </div>
        </div>

        {/* Error Count */}
        {progress.errors > 0 && (
          <div className="bg-red-900/20 border border-red-800 rounded-lg p-3">
            <p className="text-red-400 text-sm">
              ⚠️ {progress.errors} RFPs failed to process
            </p>
          </div>
        )}

        {/* Estimated Time */}
        <div className="text-center text-gray-400 text-sm">
          {progress.processed > 0 && progress.processed < progress.found && (
            <p>
              Estimated time remaining:{' '}
              {estimateTimeRemaining(
                progress.found - progress.processed,
                progress.processed,
                new Date(run.started_at)
              )}
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}

function estimateTimeRemaining(
  remaining: number,
  processed: number,
  startTime: Date
): string {
  if (processed === 0) return 'calculating...'

  const elapsedMs = Date.now() - startTime.getTime()
  const avgTimePerRfp = elapsedMs / processed
  const remainingMs = remaining * avgTimePerRfp

  const minutes = Math.floor(remainingMs / 60000)
  const seconds = Math.floor((remainingMs % 60000) / 1000)

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}