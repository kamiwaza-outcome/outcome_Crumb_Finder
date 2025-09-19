'use client'

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { toast } from '@/components/ui/toast'
import { CronBuilder } from './CronBuilder'

interface Model {
  name: string
  displayName: string
  vendor: string
}

interface Schedule {
  schedule_id: string
  name: string
  run_mode: 'test' | 'normal' | 'overkill'
  cron_expression: string
  enabled: boolean
  last_run?: string
  next_run?: string
  search_config: {
    batch_size: number
    days_back: number
    max_rfps: number
    model_name: string
  }
}

interface ScheduleManagerProps {
  onScheduleChange?: () => void
}

export function ScheduleManager({ onScheduleChange }: ScheduleManagerProps) {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [showCronBuilder, setShowCronBuilder] = useState(false)
  const [cronDescription, setCronDescription] = useState<string>('')

  // Dynamic defaults based on run mode
  const getDefaultValues = (mode: 'test' | 'normal' | 'overkill') => {
    switch (mode) {
      case 'test':
        return { max_rfps: 20, days_back: 1, batch_size: 10 }
      case 'normal':
        return { max_rfps: 500, days_back: 1, batch_size: 32 }
      case 'overkill':
        return { max_rfps: 20000, days_back: 1, batch_size: 64 }
      default:
        return { max_rfps: 200, days_back: 1, batch_size: 32 }
    }
  }

  const [newSchedule, setNewSchedule] = useState<Partial<Schedule>>({
    name: '',
    run_mode: 'normal',
    cron_expression: '0 17 * * *',
    enabled: true,
    search_config: {
      batch_size: 32,
      days_back: 1,
      max_rfps: 500,
      model_name: ''
    }
  })

  const predefinedSchedules = [
    { id: 'morning', name: 'Morning Check', cron: '0 9 * * TUE,WED,THU,FRI,SAT', mode: 'normal' as const, desc: 'Tue-Sat at 9 AM' },
    { id: 'evening', name: 'Evening Review', cron: '0 17 * * *', mode: 'normal' as const, desc: 'Daily at 5 PM' },
    { id: 'test', name: 'Quick Test', cron: '*/15 * * * *', mode: 'test' as const, desc: 'Every 15 minutes (test)' },
    { id: 'weekly', name: 'Weekly Deep Scan', cron: '0 9 * * MON', mode: 'overkill' as const, desc: 'Mondays at 9 AM' },
    { id: 'daily247', name: '24/7 Daily', cron: '0 9 * * *', mode: 'normal' as const, desc: 'Every day at 9 AM' },
    { id: 'custom', name: 'Custom Schedule', cron: '', mode: 'normal' as const, desc: 'Define your own' }
  ]

  useEffect(() => {
    loadSchedules()
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      const response = await api.get('/models')
      setModels(response.data || [])
      if (response.data && response.data.length > 0) {
        setNewSchedule(prev => ({
          ...prev,
          search_config: {
            ...prev.search_config!,
            model_name: response.data[0].name
          }
        }))
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  const loadSchedules = async () => {
    try {
      const response = await api.get('/rfp/schedules')
      setSchedules(response.data || [])
    } catch (error) {
      console.error('Failed to load schedules:', error)
    }
  }

  // Update defaults when run mode changes
  const handleRunModeChange = (mode: 'test' | 'normal' | 'overkill') => {
    const defaults = getDefaultValues(mode)
    setNewSchedule({
      ...newSchedule,
      run_mode: mode,
      search_config: {
        ...newSchedule.search_config!,
        ...defaults
      }
    })
  }

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId)
    const template = predefinedSchedules.find(t => t.id === templateId)
    if (template) {
      if (templateId === 'custom') {
        setShowCronBuilder(true)
        setCronDescription('')
      } else {
        setShowCronBuilder(false)
        setCronDescription('')
      }
      const defaults = getDefaultValues(template.mode)
      setNewSchedule({
        ...newSchedule,
        name: template.name,
        cron_expression: template.cron,
        run_mode: template.mode,
        search_config: {
          ...newSchedule.search_config!,
          ...defaults
        }
      })
    }
  }

  const createSchedule = async (schedule: Partial<Schedule>) => {
    try {
      await api.post('/rfp/schedules', {
        ...schedule,
        schedule_id: `schedule_${Date.now()}`
      })
      toast.success(`Schedule "${schedule.name}" created`)
      await loadSchedules()
      onScheduleChange?.()
      setIsCreating(false)
      setSelectedTemplate('')
    } catch (error) {
      console.error('Failed to create schedule:', error)
      toast.error('Failed to create schedule')
    }
  }

  const toggleSchedule = async (scheduleId: string, enabled: boolean) => {
    try {
      await api.put(`/rfp/schedules/${scheduleId}`, { enabled })
      toast.success(enabled ? 'Schedule enabled' : 'Schedule disabled')
      await loadSchedules()
      onScheduleChange?.()
    } catch (error) {
      console.error('Failed to toggle schedule:', error)
      toast.error('Failed to update schedule')
    }
  }

  const deleteSchedule = async (scheduleId: string) => {
    try {
      await api.delete(`/rfp/schedules/${scheduleId}`)
      toast.success('Schedule deleted')
      await loadSchedules()
      onScheduleChange?.()
    } catch (error) {
      console.error('Failed to delete schedule:', error)
      toast.error('Failed to delete schedule')
    }
  }

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'test': return 'text-blue-500'
      case 'normal': return 'text-green-500'
      case 'overkill': return 'text-red-500'
      default: return 'text-gray-500'
    }
  }

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case 'test': return '🧪'
      case 'normal': return '✓'
      case 'overkill': return '🚀'
      default: return ''
    }
  }

  return (
    <Card className="bg-gray-800 border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Schedule Management</h2>
        <Button
          onClick={() => setIsCreating(!isCreating)}
          className="bg-kamiwaza-blue hover:bg-kamiwaza-blue-dark"
        >
          {isCreating ? 'Cancel' : 'New Schedule'}
        </Button>
      </div>

      {isCreating && (
        <div className="mb-6 p-4 bg-gray-900 rounded-lg">
          <h3 className="text-lg font-medium mb-4">Create New Schedule</h3>

          {/* Template Selection */}
          <div className="mb-4">
            <p className="text-sm text-gray-400 mb-2">Choose a Template:</p>
            <div className="grid grid-cols-3 gap-2">
              {predefinedSchedules.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleTemplateSelect(template.id)}
                  className={`p-2 text-xs rounded border transition-all ${
                    selectedTemplate === template.id
                      ? 'bg-kamiwaza-blue border-kamiwaza-blue text-white'
                      : 'bg-gray-800 hover:bg-gray-700 border-gray-600'
                  }`}
                >
                  <div className="font-medium">{template.name} {getModeIcon(template.mode)}</div>
                  <div className="text-gray-400">{template.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Schedule Name
              </label>
              <input
                type="text"
                value={newSchedule.name || ''}
                onChange={(e) => setNewSchedule({ ...newSchedule, name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
                placeholder="e.g., Morning Discovery"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Cron Expression
              </label>
              {showCronBuilder ? (
                <div>
                  <input
                    type="text"
                    value={newSchedule.cron_expression || ''}
                    readOnly
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white mb-2"
                    placeholder="Auto-generated from builder below"
                  />
                  {cronDescription && (
                    <p className="text-sm text-kamiwaza-blue mb-2">{cronDescription}</p>
                  )}
                </div>
              ) : (
                <input
                  type="text"
                  value={newSchedule.cron_expression || ''}
                  onChange={(e) => setNewSchedule({ ...newSchedule, cron_expression: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
                  placeholder="0 17 * * * (5PM daily)"
                />
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                AI Model
              </label>
              <select
                value={newSchedule.search_config?.model_name || ''}
                onChange={(e) => setNewSchedule({
                  ...newSchedule,
                  search_config: {
                    ...newSchedule.search_config!,
                    model_name: e.target.value
                  }
                })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
              >
                {models.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.displayName || model.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Run Mode
              </label>
              <select
                value={newSchedule.run_mode || 'normal'}
                onChange={(e) => handleRunModeChange(e.target.value as 'test' | 'normal' | 'overkill')}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
              >
                <option value="test">Test 🧪 (Quick, 20 RFPs)</option>
                <option value="normal">Normal ✓ (Standard, 500 RFPs)</option>
                <option value="overkill">Overkill 🚀 (Deep, 20K RFPs)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Batch Size (Concurrent)
              </label>
              <input
                type="number"
                min="1"
                max="128"
                value={newSchedule.search_config?.batch_size || 32}
                onChange={(e) => setNewSchedule({
                  ...newSchedule,
                  search_config: {
                    ...newSchedule.search_config!,
                    batch_size: parseInt(e.target.value)
                  }
                })}
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
                value={newSchedule.search_config?.max_rfps || 500}
                onChange={(e) => setNewSchedule({
                  ...newSchedule,
                  search_config: {
                    ...newSchedule.search_config!,
                    max_rfps: parseInt(e.target.value)
                  }
                })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
              />
              <p className="text-xs text-gray-500 mt-1">
                {newSchedule.run_mode === 'test' && 'Default: 20 for quick testing'}
                {newSchedule.run_mode === 'normal' && 'Default: 500 for daily operations'}
                {newSchedule.run_mode === 'overkill' && 'Default: 20,000 for comprehensive analysis'}
              </p>
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Days to Search Back
              </label>
              <input
                type="number"
                min="1"
                max="30"
                value={newSchedule.search_config?.days_back || 1}
                onChange={(e) => setNewSchedule({
                  ...newSchedule,
                  search_config: {
                    ...newSchedule.search_config!,
                    days_back: parseInt(e.target.value)
                  }
                })}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
              />
              <p className="text-xs text-gray-500 mt-1">
                Search for RFPs posted within the last {newSchedule.search_config?.days_back || 1} day(s)
              </p>
            </div>
          </div>

          {/* Visual Cron Builder for Custom Schedules */}
          {showCronBuilder && (
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Schedule Builder
              </label>
              <CronBuilder
                value={newSchedule.cron_expression || '0 17 * * *'}
                onChange={(cron) => setNewSchedule({ ...newSchedule, cron_expression: cron })}
                onDescriptionChange={setCronDescription}
              />
            </div>
          )}

          <div className="mt-4 flex gap-2">
            <Button
              onClick={() => createSchedule(newSchedule)}
              disabled={!newSchedule.name || !newSchedule.cron_expression}
              className="bg-green-600 hover:bg-green-700"
            >
              Create Schedule
            </Button>
            <Button
              onClick={() => {
                setIsCreating(false)
                setSelectedTemplate('')
                setShowCronBuilder(false)
                setCronDescription('')
              }}
              variant="outline"
              className="border-gray-600 text-gray-300 hover:bg-gray-700"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Existing Schedules */}
      <div className="space-y-3">
        {schedules.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p>No schedules configured yet</p>
            <p className="text-sm mt-2">Create your first schedule to automate RFP discovery</p>
          </div>
        ) : (
          schedules.map((schedule) => (
            <div
              key={schedule.schedule_id}
              className="flex items-center justify-between p-3 bg-gray-900 rounded-lg"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium">{schedule.name}</span>
                  <span className={`text-sm ${getModeColor(schedule.run_mode)}`}>
                    {getModeIcon(schedule.run_mode)} {schedule.run_mode}
                  </span>
                  {!schedule.enabled && (
                    <span className="text-xs px-2 py-0.5 bg-gray-700 text-gray-400 rounded">
                      Disabled
                    </span>
                  )}
                </div>
                <div className="text-sm text-gray-400 mt-1">
                  <span className="font-mono">{schedule.cron_expression}</span>
                  <span className="mx-2">•</span>
                  <span>Model: {schedule.search_config.model_name}</span>
                  <span className="mx-2">•</span>
                  <span>Batch: {schedule.search_config.batch_size}</span>
                  <span className="mx-2">•</span>
                  <span>Max: {schedule.search_config.max_rfps} RFPs</span>
                  <span className="mx-2">•</span>
                  <span>{schedule.search_config.days_back} day(s) back</span>
                  {schedule.next_run && (
                    <>
                      <span className="mx-2">•</span>
                      <span>Next: {new Date(schedule.next_run).toLocaleString()}</span>
                    </>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleSchedule(schedule.schedule_id, !schedule.enabled)}
                  className={schedule.enabled ? "text-green-500" : "text-gray-500"}
                >
                  {schedule.enabled ? 'Enabled' : 'Disabled'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => deleteSchedule(schedule.schedule_id)}
                  className="text-red-500 hover:text-red-400"
                >
                  Delete
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  )
}