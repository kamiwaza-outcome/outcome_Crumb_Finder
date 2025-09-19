'use client'

import { cn } from '@/lib/utils'

interface Model {
  name: string
  displayName?: string
  vendor?: string
}

interface ModelSelectorProps {
  models: Model[]
  selectedModel: string
  onModelChange: (model: string) => void
  className?: string
}

export function ModelSelector({
  models,
  selectedModel,
  onModelChange,
  className
}: ModelSelectorProps) {
  if (models.length === 0) {
    return (
      <select
        disabled
        className={cn(
          "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-500",
          className
        )}
      >
        <option>No models available</option>
      </select>
    )
  }

  return (
    <select
      value={selectedModel}
      onChange={(e) => onModelChange(e.target.value)}
      className={cn(
        "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white",
        "focus:outline-none focus:ring-2 focus:ring-kamiwaza-green focus:border-transparent",
        "cursor-pointer hover:bg-gray-800 transition-colors",
        className
      )}
    >
      {models.map((model) => (
        <option key={model.name} value={model.name}>
          {model.displayName || model.name}
          {model.vendor && ` (${model.vendor})`}
        </option>
      ))}
    </select>
  )
}