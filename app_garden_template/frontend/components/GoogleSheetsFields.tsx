import React from 'react'

interface GoogleSheetsFieldsProps {
  settings: any
  setSettings: (settings: any) => void
}

export function GoogleSheetsFields({ settings, setSettings }: GoogleSheetsFieldsProps) {
  const sheets = [
    {
      key: 'qualified_sheet_id',
      label: '✅ Qualified Sheet',
      placeholder: 'Sheet ID for qualified RFPs to pursue',
      description: 'High-priority RFPs that match your capabilities'
    },
    {
      key: 'maybe_sheet_id',
      label: '🤔 Maybe Sheet',
      placeholder: 'Sheet ID for RFPs needing review',
      description: 'RFPs that need further evaluation'
    },
    {
      key: 'rejected_sheet_id',
      label: '❌ Rejected Sheet',
      placeholder: 'Sheet ID for rejected/spam RFPs',
      description: 'Irrelevant or low-quality RFPs'
    },
    {
      key: 'graveyard_sheet_id',
      label: '⚰️ Graveyard Sheet',
      placeholder: 'Sheet ID for expired opportunities',
      description: 'Lost or expired RFPs for historical reference'
    },
    {
      key: 'bank_sheet_id',
      label: '🏦 Bank Sheet',
      placeholder: 'Sheet ID for historical RFP data',
      description: 'Archive of all processed RFPs for analysis'
    },
  ]

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white mb-2">Google Sheets Configuration</h3>
      <p className="text-sm text-gray-400 mb-4">
        Configure sheets for the RFP qualification workflow. Share each sheet with your service account email.
      </p>

      {sheets.map((sheet) => (
        <div key={sheet.key} className="bg-gray-700/50 rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            {sheet.label}
          </label>
          <input
            type="text"
            value={settings.api_keys.google_sheets[sheet.key] || ''}
            onChange={(e) => setSettings({
              ...settings,
              api_keys: {
                ...settings.api_keys,
                google_sheets: {
                  ...settings.api_keys.google_sheets,
                  [sheet.key]: e.target.value
                }
              }
            })}
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
            placeholder={sheet.placeholder}
          />
          <p className="text-xs text-gray-500 mt-1">{sheet.description}</p>
        </div>
      ))}
    </div>
  )
}