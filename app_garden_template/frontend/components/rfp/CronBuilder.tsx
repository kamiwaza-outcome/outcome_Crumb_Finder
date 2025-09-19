'use client'

import React, { useState, useEffect } from 'react'

interface CronBuilderProps {
  value: string
  onChange: (cron: string) => void
  onDescriptionChange?: (description: string) => void
}

export function CronBuilder({ value, onChange, onDescriptionChange }: CronBuilderProps) {
  const [frequency, setFrequency] = useState<'minutes' | 'hourly' | 'daily' | 'weekly' | 'monthly'>('daily')
  const [minuteInterval, setMinuteInterval] = useState(15)
  const [hour, setHour] = useState(9)
  const [minute, setMinute] = useState(0)
  const [dayOfWeek, setDayOfWeek] = useState<number[]>([2, 3, 4, 5, 6]) // Tuesday-Saturday (SAM.gov posting days)
  const [dailyMode, setDailyMode] = useState<'everyday' | 'weekdays'>('weekdays')
  const [dayOfMonth, setDayOfMonth] = useState(1)
  const [monthlyFrequency, setMonthlyFrequency] = useState<'specific' | 'first' | 'last'>('specific')

  const weekDays = [
    { value: 0, label: 'Sun', short: 'SUN' },
    { value: 1, label: 'Mon', short: 'MON' },
    { value: 2, label: 'Tue', short: 'TUE' },
    { value: 3, label: 'Wed', short: 'WED' },
    { value: 4, label: 'Thu', short: 'THU' },
    { value: 5, label: 'Fri', short: 'FRI' },
    { value: 6, label: 'Sat', short: 'SAT' }
  ]

  const hours = Array.from({ length: 24 }, (_, i) => i)
  const minutes = Array.from({ length: 60 }, (_, i) => i)

  useEffect(() => {
    buildCron()
  }, [frequency, minuteInterval, hour, minute, dayOfWeek, dailyMode, dayOfMonth, monthlyFrequency])

  const buildCron = () => {
    let cron = ''
    let description = ''

    switch (frequency) {
      case 'minutes':
        cron = `*/${minuteInterval} * * * *`
        description = `Every ${minuteInterval} minutes`
        break

      case 'hourly':
        cron = `${minute} * * * *`
        description = `Every hour at :${minute.toString().padStart(2, '0')}`
        break

      case 'daily':
        const timeStr = `${hour > 12 ? hour - 12 : hour === 0 ? 12 : hour}:${minute.toString().padStart(2, '0')} ${hour >= 12 ? 'PM' : 'AM'}`
        if (dailyMode === 'everyday') {
          cron = `${minute} ${hour} * * *`
          description = `Every day at ${timeStr}`
        } else {
          // Weekdays mode with specific day selection
          if (dayOfWeek.length === 0) return
          const days = dayOfWeek.sort((a, b) => a - b).map(d => weekDays[d].short).join(',')
          cron = `${minute} ${hour} * * ${days}`
          const dayNames = dayOfWeek.sort((a, b) => a - b).map(d => weekDays[d].label).join(', ')
          description = `Every ${dayNames} at ${timeStr}`
        }
        break

      case 'weekly':
        if (dayOfWeek.length === 0) return
        const days = dayOfWeek.sort((a, b) => a - b).map(d => weekDays[d].short).join(',')
        cron = `${minute} ${hour} * * ${days}`
        const weekTimeStr = `${hour > 12 ? hour - 12 : hour === 0 ? 12 : hour}:${minute.toString().padStart(2, '0')} ${hour >= 12 ? 'PM' : 'AM'}`
        const dayNames = dayOfWeek.sort((a, b) => a - b).map(d => weekDays[d].label).join(', ')
        description = `Every ${dayNames} at ${weekTimeStr}`
        break

      case 'monthly':
        if (monthlyFrequency === 'specific') {
          cron = `${minute} ${hour} ${dayOfMonth} * *`
          const monthTimeStr = `${hour > 12 ? hour - 12 : hour === 0 ? 12 : hour}:${minute.toString().padStart(2, '0')} ${hour >= 12 ? 'PM' : 'AM'}`
          const suffix = dayOfMonth === 1 ? 'st' : dayOfMonth === 2 ? 'nd' : dayOfMonth === 3 ? 'rd' : 'th'
          description = `Monthly on the ${dayOfMonth}${suffix} at ${monthTimeStr}`
        } else if (monthlyFrequency === 'first') {
          cron = `${minute} ${hour} 1 * *`
          const monthTimeStr = `${hour > 12 ? hour - 12 : hour === 0 ? 12 : hour}:${minute.toString().padStart(2, '0')} ${hour >= 12 ? 'PM' : 'AM'}`
          description = `First day of every month at ${monthTimeStr}`
        } else {
          cron = `${minute} ${hour} L * *` // L means last day
          const monthTimeStr = `${hour > 12 ? hour - 12 : hour === 0 ? 12 : hour}:${minute.toString().padStart(2, '0')} ${hour >= 12 ? 'PM' : 'AM'}`
          description = `Last day of every month at ${monthTimeStr}`
        }
        break
    }

    onChange(cron)
    if (onDescriptionChange) {
      onDescriptionChange(description)
    }
  }

  const toggleWeekDay = (day: number) => {
    if (dayOfWeek.includes(day)) {
      setDayOfWeek(dayOfWeek.filter(d => d !== day))
    } else {
      setDayOfWeek([...dayOfWeek, day])
    }
  }

  return (
    <div className="space-y-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
      <div>
        <label className="block text-sm font-medium text-gray-400 mb-2">
          Frequency
        </label>
        <div className="flex gap-2 flex-wrap">
          {['minutes', 'hourly', 'daily', 'weekly', 'monthly'].map((freq) => (
            <button
              key={freq}
              onClick={() => setFrequency(freq as any)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                frequency === freq
                  ? 'bg-kamiwaza-blue text-white'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              {freq.charAt(0).toUpperCase() + freq.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {frequency === 'minutes' && (
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Every how many minutes?
          </label>
          <select
            value={minuteInterval}
            onChange={(e) => setMinuteInterval(parseInt(e.target.value))}
            className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
          >
            <option value="5">5 minutes</option>
            <option value="10">10 minutes</option>
            <option value="15">15 minutes</option>
            <option value="30">30 minutes</option>
          </select>
        </div>
      )}

      {frequency === 'daily' && (
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Daily Mode
          </label>
          <div className="flex gap-2 mb-3">
            <button
              onClick={() => setDailyMode('everyday')}
              className={`px-3 py-1 rounded-lg text-sm ${
                dailyMode === 'everyday'
                  ? 'bg-kamiwaza-blue text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              Every Day
            </button>
            <button
              onClick={() => {
                setDailyMode('weekdays')
                // Default to Tuesday-Saturday for SAM.gov
                if (dayOfWeek.length === 0) {
                  setDayOfWeek([2, 3, 4, 5, 6])
                }
              }}
              className={`px-3 py-1 rounded-lg text-sm ${
                dailyMode === 'weekdays'
                  ? 'bg-kamiwaza-blue text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              Selected Days
            </button>
          </div>
          {dailyMode === 'weekdays' && (
            <>
              <div className="flex gap-2 mb-2">
                {weekDays.map(day => (
                  <button
                    key={day.value}
                    onClick={() => toggleWeekDay(day.value)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                      dayOfWeek.includes(day.value)
                        ? 'bg-kamiwaza-blue text-white'
                        : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                    }`}
                  >
                    {day.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500">
                Recommended: Tue-Sat (SAM.gov typically posts new RFPs on weekdays)
              </p>
            </>
          )}
        </div>
      )}

      {(frequency === 'hourly' || frequency === 'daily' || frequency === 'weekly' || frequency === 'monthly') && (
        <div className="grid grid-cols-2 gap-4">
          {frequency !== 'hourly' && (
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Hour
              </label>
              <select
                value={hour}
                onChange={(e) => setHour(parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
              >
                {hours.map(h => (
                  <option key={h} value={h}>
                    {h === 0 ? '12 AM' : h < 12 ? `${h} AM` : h === 12 ? '12 PM' : `${h - 12} PM`}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className={frequency === 'hourly' ? 'col-span-2' : ''}>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Minute
            </label>
            <select
              value={minute}
              onChange={(e) => setMinute(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            >
              <option value="0">:00</option>
              <option value="15">:15</option>
              <option value="30">:30</option>
              <option value="45">:45</option>
              {Array.from({ length: 60 }, (_, i) => i).map(m => (
                <option key={m} value={m}>:{m.toString().padStart(2, '0')}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {frequency === 'weekly' && (
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Days of the Week
          </label>
          <div className="flex gap-2">
            {weekDays.map(day => (
              <button
                key={day.value}
                onClick={() => toggleWeekDay(day.value)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  dayOfWeek.includes(day.value)
                    ? 'bg-kamiwaza-blue text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                {day.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {frequency === 'monthly' && (
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Day of Month
          </label>
          <div className="flex gap-2 mb-2">
            <button
              onClick={() => setMonthlyFrequency('specific')}
              className={`px-3 py-1 rounded-lg text-sm ${
                monthlyFrequency === 'specific'
                  ? 'bg-kamiwaza-blue text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              Specific Day
            </button>
            <button
              onClick={() => setMonthlyFrequency('first')}
              className={`px-3 py-1 rounded-lg text-sm ${
                monthlyFrequency === 'first'
                  ? 'bg-kamiwaza-blue text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              First Day
            </button>
            <button
              onClick={() => setMonthlyFrequency('last')}
              className={`px-3 py-1 rounded-lg text-sm ${
                monthlyFrequency === 'last'
                  ? 'bg-kamiwaza-blue text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              Last Day
            </button>
          </div>
          {monthlyFrequency === 'specific' && (
            <select
              value={dayOfMonth}
              onChange={(e) => setDayOfMonth(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white"
            >
              {Array.from({ length: 28 }, (_, i) => i + 1).map(d => (
                <option key={d} value={d}>
                  {d}{d === 1 ? 'st' : d === 2 ? 'nd' : d === 3 ? 'rd' : 'th'}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      <div className="pt-2 border-t border-gray-700">
        <p className="text-sm text-gray-400">
          Generated Cron: <span className="font-mono text-white">{value}</span>
        </p>
      </div>
    </div>
  )
}