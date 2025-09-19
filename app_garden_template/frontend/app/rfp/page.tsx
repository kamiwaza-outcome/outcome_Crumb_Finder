'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/loading-spinner'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { toast } from '@/components/ui/toast'
import { RFPTable } from '@/components/rfp/RFPTable'
import { RunMonitor } from '@/components/rfp/RunMonitor'
import { LogViewer } from '@/components/rfp/LogViewer'
import { ScheduleManager } from '@/components/rfp/ScheduleManager'
import { ModelSelector } from '@/components/model-selector'

interface Model {
  name: string
  displayName: string
  vendor: string
}

interface RFPSearchConfig {
  search_keywords: string[]
  days_back: number
  max_rfps: number
  model_name: string
  batch_size: number
  run_mode: 'test' | 'normal' | 'overkill'
}

interface DaemonStatus {
  is_running: boolean
  uptime_seconds: number
  current_run: any | null
  recent_runs: any[]
  active_schedules: any[]
}

export default function RFPDiscoveryPage() {
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [daemonStatus, setDaemonStatus] = useState<DaemonStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [showLogs, setShowLogs] = useState(false)

  // Search configuration
  const [searchConfig, setSearchConfig] = useState<RFPSearchConfig>({
    search_keywords: [
      'artificial intelligence',
      'machine learning',
      'data analytics',
      'automation',
      'software development'
    ],
    days_back: 3,
    max_rfps: 200,
    model_name: '',
    batch_size: 32,
    run_mode: 'normal'
  })

  // Load models and daemon status on mount
  useEffect(() => {
    loadInitialData()
    const interval = setInterval(refreshStatus, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const loadInitialData = async () => {
    try {
      setIsLoading(true)

      // Load available models
      const modelsResponse = await api.get('/models')
      if (modelsResponse.data) {
        setModels(modelsResponse.data)
        if (modelsResponse.data.length > 0) {
          setSelectedModel(modelsResponse.data[0].name)
          setSearchConfig(prev => ({
            ...prev,
            model_name: modelsResponse.data[0].name
          }))
        }
      }

      // Load daemon status
      await refreshStatus()
    } catch (error) {
      console.error('Failed to load initial data:', error)
      toast.error('Failed to load RFP discovery data')
    } finally {
      setIsLoading(false)
    }
  }

  const refreshStatus = async () => {
    try {
      const statusResponse = await api.get('/rfp/daemon/status')
      setDaemonStatus(statusResponse.data)
    } catch (error) {
      console.error('Failed to refresh status:', error)
    }
  }

  const startDaemon = async () => {
    try {
      await api.post('/rfp/daemon/start')
      toast.success('RFP Discovery daemon started')
      await refreshStatus()
    } catch (error) {
      console.error('Failed to start daemon:', error)
      toast.error('Failed to start daemon')
    }
  }

  const stopDaemon = async () => {
    try {
      await api.post('/rfp/daemon/stop')
      toast.success('RFP Discovery daemon stopped')
      await refreshStatus()
    } catch (error) {
      console.error('Failed to stop daemon:', error)
      toast.error('Failed to stop daemon')
    }
  }

  const triggerDiscovery = async () => {
    if (!searchConfig.model_name) {
      toast.error('Please select a model first')
      return
    }

    try {
      setIsDiscovering(true)
      const response = await api.post('/rfp/discover/background', searchConfig)
      toast.success('RFP discovery started in background')
      await refreshStatus()
    } catch (error) {
      console.error('Failed to trigger discovery:', error)
      toast.error('Failed to start discovery')
    } finally {
      setIsDiscovering(false)
    }
  }


  const viewRunLogs = (runId: string) => {
    setSelectedRunId(runId)
    setShowLogs(true)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">RFP Discovery System</h1>
          <p className="text-gray-400 mt-2">
            Automated discovery and qualification of government RFP opportunities
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Button
            onClick={() => window.location.href = '/settings'}
            variant="outline"
            className="border-gray-600 text-gray-300 hover:bg-gray-700"
          >
            ⚙️ Settings
          </Button>
          {daemonStatus?.is_running ? (
            <Button
              onClick={stopDaemon}
              variant="destructive"
              className="bg-red-600 hover:bg-red-700"
            >
              Stop Daemon
            </Button>
          ) : (
            <Button
              onClick={startDaemon}
              className="bg-green-600 hover:bg-green-700"
            >
              Start Daemon
            </Button>
          )}
        </div>
      </div>

      {/* Status Card */}
      <Card className="bg-gray-800 border-gray-700 p-6">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <p className="text-gray-400 text-sm">Daemon Status</p>
            <p className="text-2xl font-bold">
              {daemonStatus?.is_running ? (
                <span className="text-green-500">Running</span>
              ) : (
                <span className="text-red-500">Stopped</span>
              )}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Uptime</p>
            <p className="text-2xl font-bold text-white">
              {daemonStatus ? formatUptime(daemonStatus.uptime_seconds) : '—'}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Active Schedules</p>
            <p className="text-2xl font-bold text-white">
              {daemonStatus?.active_schedules?.length || 0}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Total Runs</p>
            <p className="text-2xl font-bold text-white">
              {daemonStatus?.recent_runs?.length || 0}
            </p>
          </div>
        </div>
      </Card>

      {/* Discovery Controls */}
      <Card className="bg-gray-800 border-gray-700 p-6">
        <h2 className="text-xl font-semibold mb-4">Discovery Configuration</h2>

        <div className="space-y-4">
          {/* AI Model - Full Width */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              AI Model
            </label>
            <ModelSelector
              models={models}
              selectedModel={selectedModel}
              onModelChange={(model) => {
                setSelectedModel(model)
                setSearchConfig(prev => ({ ...prev, model_name: model }))
              }}
            />
          </div>

          {/* Days Back and Max RFPs - Side by Side */}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Days to Search Back
              </label>
              <input
                type="number"
                min="1"
                max="30"
                value={searchConfig.days_back}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  days_back: parseInt(e.target.value)
                }))}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Max RFPs to Process
              </label>
              <input
                type="number"
                min="1"
                max="20000"
                value={searchConfig.max_rfps}
                onChange={(e) => setSearchConfig(prev => ({
                  ...prev,
                  max_rfps: parseInt(e.target.value)
                }))}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
              />
            </div>
          </div>

          {/* Run Mode and Batch Size - Side by Side */}
          <div className="grid grid-cols-2 gap-6">

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Batch Size (Concurrent Processing)
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="1"
                  max="128"
                  value={searchConfig.batch_size}
                  onChange={(e) => setSearchConfig(prev => ({
                    ...prev,
                    batch_size: parseInt(e.target.value)
                  }))}
                  className="flex-1"
                />
                <span className="text-white font-mono w-12 text-right">
                  {searchConfig.batch_size}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Higher values = faster processing but more resource intensive
              </p>
            </div>
          </div>
        </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Run Mode
              </label>
              <div className="flex gap-2">
                {(['test', 'normal', 'overkill'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setSearchConfig(prev => ({ ...prev, run_mode: mode }))}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      searchConfig.run_mode === mode
                        ? mode === 'test'
                          ? 'bg-blue-600 text-white'
                          : mode === 'normal'
                          ? 'bg-green-600 text-white'
                          : 'bg-red-600 text-white'
                        : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                    }`}
                  >
                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                    {mode === 'test' && ' 🧪'}
                    {mode === 'normal' && ' ✓'}
                    {mode === 'overkill' && ' 🚀'}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {searchConfig.run_mode === 'test' && 'Quick run with minimal processing for testing'}
                {searchConfig.run_mode === 'normal' && 'Standard processing for daily operations'}
                {searchConfig.run_mode === 'overkill' && 'Maximum depth analysis for critical opportunities'}
              </p>
            </div>

        <div className="mt-6">
          <Button
            onClick={triggerDiscovery}
            disabled={isDiscovering || !daemonStatus?.is_running}
            className="bg-kamiwaza-green hover:bg-kamiwaza-green-dark"
          >
            {isDiscovering ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Discovering...
              </>
            ) : (
              'Run Discovery Now'
            )}
          </Button>
        </div>
      </Card>

      {/* Schedule Management */}
      <ScheduleManager onScheduleChange={refreshStatus} />

      {/* Current Run Monitor */}
      {daemonStatus?.current_run && (
        <RunMonitor run={daemonStatus.current_run} />
      )}

      {/* Recent Runs */}
      {daemonStatus?.recent_runs && daemonStatus.recent_runs.length > 0 && (
        <Card className="bg-gray-800 border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Discovery Runs</h2>
          <div className="space-y-2">
            {daemonStatus.recent_runs.slice(0, 5).map((run: any) => (
              <div
                key={run.run_id}
                className="flex items-center justify-between p-3 bg-gray-900 rounded-lg"
              >
                <div>
                  <p className="text-white font-medium">{run.run_id}</p>
                  <p className="text-gray-400 text-sm">
                    {new Date(run.started_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm text-gray-400">
                      Found: {run.total_found} | Qualified: {run.total_qualified}
                    </p>
                    <p className="text-xs text-gray-500">
                      {run.processing_time_seconds?.toFixed(1)}s
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => viewRunLogs(run.run_id)}
                    className="text-kamiwaza-blue hover:text-kamiwaza-blue-light"
                  >
                    View Logs
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Discovered RFPs Table */}
      <RFPTable />

      {/* Log Viewer Modal */}
      {showLogs && selectedRunId && (
        <LogViewer
          runId={selectedRunId}
          onClose={() => {
            setShowLogs(false)
            setSelectedRunId(null)
          }}
        />
      )}
    </div>
  )
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`
  return `${Math.floor(seconds / 86400)}d`
}