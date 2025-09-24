'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { Plus, Trash2, Save, ArrowLeft } from 'lucide-react'

interface GoogleSheetsConfig {
  rfp_tracking_sheet_id: string
  opportunity_pipeline_sheet_id: string
  win_loss_analysis_sheet_id: string
  competitor_tracking_sheet_id: string
  reporting_dashboard_sheet_id: string
}

interface APIKeys {
  sam_gov_api_key: string
  google_service_account_json: string
  google_sheets: GoogleSheetsConfig
}

interface PastPerformanceEntry {
  contract_value: string
  client: string
  title: string
  description: string
  technologies: string[]
  outcomes: string
  year: string
}

interface CompanyProfile {
  name: string
  description: string
  capabilities: string[]
  certifications: string[]
  differentiators: string[]
  naics_codes: string[]
  cage_code: string
  sam_uei: string
  past_performance: string[]
  detailed_past_performance: PastPerformanceEntry[]
  target_rfp_examples: string
  technical_approach_templates: string
  pricing_strategies: string
}

interface Settings {
  api_keys: APIKeys
  company_profile: CompanyProfile
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    api_keys: {
      sam_gov_api_key: '',
      google_service_account_json: '',
      google_sheets: {
        rfp_tracking_sheet_id: '',
        opportunity_pipeline_sheet_id: '',
        win_loss_analysis_sheet_id: '',
        competitor_tracking_sheet_id: '',
        reporting_dashboard_sheet_id: ''
      }
    },
    company_profile: {
      name: '',
      description: '',
      capabilities: [],
      certifications: [],
      differentiators: [],
      naics_codes: [],
      cage_code: '',
      sam_uei: '',
      past_performance: [],
      detailed_past_performance: [],
      target_rfp_examples: '',
      technical_approach_templates: '',
      pricing_strategies: ''
    }
  })

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'basic' | 'integrations' | 'experience' | 'context'>('basic')

  // Text inputs for array fields
  const [capabilitiesText, setCapabilitiesText] = useState('')
  const [certificationsText, setCertificationsText] = useState('')
  const [differentiatorsText, setDifferentiatorsText] = useState('')
  const [naicsText, setNaicsText] = useState('')

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    setLoading(true)
    try {
      const response = await api.get('/rfp/settings')
      const data = response.data
      setSettings(data)

      // Convert arrays to text for editing
      setCapabilitiesText(data.company_profile.capabilities.join('\n'))
      setCertificationsText(data.company_profile.certifications.join('\n'))
      setDifferentiatorsText(data.company_profile.differentiators.join('\n'))
      setNaicsText(data.company_profile.naics_codes.join('\n'))

      // Initialize detailed past performance if empty
      if (!data.company_profile.detailed_past_performance || data.company_profile.detailed_past_performance.length === 0) {
        setSettings(prev => ({
          ...prev,
          company_profile: {
            ...prev.company_profile,
            detailed_past_performance: [{
              contract_value: '',
              client: '',
              title: '',
              description: '',
              technologies: [],
              outcomes: '',
              year: ''
            }]
          }
        }))
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
    setLoading(false)
  }

  const saveSettings = async () => {
    setSaving(true)

    // Convert text areas to arrays
    const settingsToSave = {
      ...settings,
      company_profile: {
        ...settings.company_profile,
        capabilities: capabilitiesText.split('\n').filter(line => line.trim()),
        certifications: certificationsText.split('\n').filter(line => line.trim()),
        differentiators: differentiatorsText.split('\n').filter(line => line.trim()),
        naics_codes: naicsText.split('\n').filter(line => line.trim())
      }
    }

    try {
      const response = await fetch('/api/rfp/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settingsToSave),
      })

      if (!response.ok) {
        const errorData = await response.text()
        console.error('Response error:', errorData)
        throw new Error(errorData || response.statusText)
      }

      const data = await response.json()
      setMessage({ type: 'success', text: 'Settings saved successfully!' })
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      const errorMsg = error.message || 'Failed to save settings'
      setMessage({ type: 'error', text: errorMsg })
      console.error('Failed to save settings:', error)
      setTimeout(() => setMessage(null), 5000)
    }
    setSaving(false)
  }

  const addPastPerformance = () => {
    setSettings(prev => ({
      ...prev,
      company_profile: {
        ...prev.company_profile,
        detailed_past_performance: [
          ...prev.company_profile.detailed_past_performance,
          {
            contract_value: '',
            client: '',
            title: '',
            description: '',
            technologies: [],
            outcomes: '',
            year: ''
          }
        ]
      }
    }))
  }

  const removePastPerformance = (index: number) => {
    setSettings(prev => ({
      ...prev,
      company_profile: {
        ...prev.company_profile,
        detailed_past_performance: prev.company_profile.detailed_past_performance.filter((_, i) => i !== index)
      }
    }))
  }

  const updatePastPerformance = (index: number, field: keyof PastPerformanceEntry, value: any) => {
    setSettings(prev => ({
      ...prev,
      company_profile: {
        ...prev.company_profile,
        detailed_past_performance: prev.company_profile.detailed_past_performance.map((item, i) =>
          i === index ? { ...item, [field]: value } : item
        )
      }
    }))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-8">Loading Settings...</h1>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-white">RFP Discovery Settings</h1>
          <div className="flex gap-4">
            <Button
              onClick={() => window.location.href = '/rfp'}
              variant="outline"
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </Button>
            <Button
              onClick={saveSettings}
              disabled={saving}
              className="bg-kamiwaza-green hover:bg-kamiwaza-green/90 flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save All Settings'}
            </Button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 border-b border-gray-700">
          {[
            { id: 'basic', label: 'Basic Info' },
            { id: 'integrations', label: 'Integrations' },
            { id: 'experience', label: 'Past Performance' },
            { id: 'context', label: 'RFP Context' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-6 py-3 font-medium transition-all ${
                activeTab === tab.id
                  ? 'text-kamiwaza-green border-b-2 border-kamiwaza-green'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="space-y-8">
          {/* Basic Info Tab */}
          {activeTab === 'basic' && (
            <>
              <Card className="bg-gray-800 border-gray-700 p-6">
                <h2 className="text-2xl font-semibold text-white mb-6">Company Information</h2>

                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Company Name *
                      </label>
                      <input
                        type="text"
                        value={settings.company_profile.name}
                        onChange={(e) => setSettings({
                          ...settings,
                          company_profile: { ...settings.company_profile, name: e.target.value }
                        })}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                        placeholder="Your Company Name"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          CAGE Code
                        </label>
                        <input
                          type="text"
                          value={settings.company_profile.cage_code}
                          onChange={(e) => setSettings({
                            ...settings,
                            company_profile: { ...settings.company_profile, cage_code: e.target.value }
                          })}
                          className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                          placeholder="5-char code"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          SAM UEI
                        </label>
                        <input
                          type="text"
                          value={settings.company_profile.sam_uei}
                          onChange={(e) => setSettings({
                            ...settings,
                            company_profile: { ...settings.company_profile, sam_uei: e.target.value }
                          })}
                          className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                          placeholder="12-char UEI"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Company Description
                    </label>
                    <textarea
                      value={settings.company_profile.description}
                      onChange={(e) => setSettings({
                        ...settings,
                        company_profile: { ...settings.company_profile, description: e.target.value }
                      })}
                      rows={4}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="Comprehensive description of your company's mission, vision, and market position..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Core Capabilities * (one per line)
                    </label>
                    <textarea
                      value={capabilitiesText}
                      onChange={(e) => setCapabilitiesText(e.target.value)}
                      rows={6}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="AI/ML Development&#10;Cloud Architecture & Migration&#10;Data Analytics & Business Intelligence&#10;DevOps & CI/CD Implementation&#10;Cybersecurity Solutions&#10;..."
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        NAICS Codes * (one per line)
                      </label>
                      <textarea
                        value={naicsText}
                        onChange={(e) => setNaicsText(e.target.value)}
                        rows={4}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono focus:outline-none focus:border-kamiwaza-green"
                        placeholder="541511&#10;541512&#10;541519&#10;..."
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Certifications (one per line)
                      </label>
                      <textarea
                        value={certificationsText}
                        onChange={(e) => setCertificationsText(e.target.value)}
                        rows={4}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                        placeholder="ISO 27001&#10;CMMI Level 3&#10;FedRAMP Authorized&#10;..."
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Key Differentiators (one per line)
                    </label>
                    <textarea
                      value={differentiatorsText}
                      onChange={(e) => setDifferentiatorsText(e.target.value)}
                      rows={4}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="10+ years federal contracting experience&#10;100+ cleared personnel with TS/SCI&#10;24/7 SOC operations center&#10;Proprietary AI/ML frameworks&#10;..."
                    />
                  </div>
                </div>
              </Card>
            </>
          )}

          {/* Integrations Tab */}
          {activeTab === 'integrations' && (
            <>
              <Card className="bg-gray-800 border-gray-700 p-6">
                <h2 className="text-2xl font-semibold text-white mb-6">API Keys & Authentication</h2>

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      SAM.gov API Key
                    </label>
                    <input
                      type="password"
                      value={settings.api_keys.sam_gov_api_key}
                      onChange={(e) => setSettings({
                        ...settings,
                        api_keys: { ...settings.api_keys, sam_gov_api_key: e.target.value }
                      })}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="Enter your SAM.gov API key"
                    />
                    <p className="mt-2 text-sm text-gray-400">
                      Get your API key from <a href="https://open.gsa.gov/api/get-sam-api-key/" target="_blank" rel="noopener noreferrer" className="text-kamiwaza-green hover:underline">SAM.gov API Registration</a>
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Google Service Account JSON
                    </label>
                    <textarea
                      value={settings.api_keys.google_service_account_json}
                      onChange={(e) => setSettings({
                        ...settings,
                        api_keys: { ...settings.api_keys, google_service_account_json: e.target.value }
                      })}
                      rows={8}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono text-sm focus:outline-none focus:border-kamiwaza-green"
                      placeholder='Paste your complete Google Service Account JSON credentials here...'
                    />
                  </div>
                </div>
              </Card>

              <Card className="bg-gray-800 border-gray-700 p-6">
                <h2 className="text-2xl font-semibold text-white mb-6">Google Sheets Configuration</h2>
                <p className="text-gray-400 mb-6">Configure different Google Sheets for various tracking purposes. Each sheet should be shared with your service account email.</p>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      📊 RFP Tracking Sheet
                    </label>
                    <input
                      type="text"
                      value={settings.api_keys.google_sheets.rfp_tracking_sheet_id}
                      onChange={(e) => setSettings({
                        ...settings,
                        api_keys: {
                          ...settings.api_keys,
                          google_sheets: {
                            ...settings.api_keys.google_sheets,
                            rfp_tracking_sheet_id: e.target.value
                          }
                        }
                      })}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="Sheet ID for tracking discovered RFPs"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      🎯 Opportunity Pipeline Sheet
                    </label>
                    <input
                      type="text"
                      value={settings.api_keys.google_sheets.opportunity_pipeline_sheet_id}
                      onChange={(e) => setSettings({
                        ...settings,
                        api_keys: {
                          ...settings.api_keys,
                          google_sheets: {
                            ...settings.api_keys.google_sheets,
                            opportunity_pipeline_sheet_id: e.target.value
                          }
                        }
                      })}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="Sheet ID for opportunity pipeline management"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      📈 Win/Loss Analysis Sheet
                    </label>
                    <input
                      type="text"
                      value={settings.api_keys.google_sheets.win_loss_analysis_sheet_id}
                      onChange={(e) => setSettings({
                        ...settings,
                        api_keys: {
                          ...settings.api_keys,
                          google_sheets: {
                            ...settings.api_keys.google_sheets,
                            win_loss_analysis_sheet_id: e.target.value
                          }
                        }
                      })}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="Sheet ID for win/loss analysis"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      🔍 Competitor Tracking Sheet
                    </label>
                    <input
                      type="text"
                      value={settings.api_keys.google_sheets.competitor_tracking_sheet_id}
                      onChange={(e) => setSettings({
                        ...settings,
                        api_keys: {
                          ...settings.api_keys,
                          google_sheets: {
                            ...settings.api_keys.google_sheets,
                            competitor_tracking_sheet_id: e.target.value
                          }
                        }
                      })}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="Sheet ID for competitor tracking"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      📝 Reporting Dashboard Sheet
                    </label>
                    <input
                      type="text"
                      value={settings.api_keys.google_sheets.reporting_dashboard_sheet_id}
                      onChange={(e) => setSettings({
                        ...settings,
                        api_keys: {
                          ...settings.api_keys,
                          google_sheets: {
                            ...settings.api_keys.google_sheets,
                            reporting_dashboard_sheet_id: e.target.value
                          }
                        }
                      })}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder="Sheet ID for reporting and metrics"
                    />
                  </div>
                </div>
              </Card>
            </>
          )}

          {/* Past Performance Tab */}
          {activeTab === 'experience' && (
            <>
              <Card className="bg-gray-800 border-gray-700 p-6">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-semibold text-white">Past Performance & Contract History</h2>
                  <Button
                    onClick={addPastPerformance}
                    className="bg-kamiwaza-green hover:bg-kamiwaza-green/90 flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Contract
                  </Button>
                </div>

                <div className="space-y-6">
                  {settings.company_profile.detailed_past_performance.map((perf, index) => (
                    <div key={index} className="border border-gray-700 rounded-lg p-6 space-y-4">
                      <div className="flex justify-between items-start">
                        <h3 className="text-lg font-medium text-white">Contract #{index + 1}</h3>
                        <button
                          onClick={() => removePastPerformance(index)}
                          className="text-red-500 hover:text-red-400"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-1">
                            Contract Value
                          </label>
                          <input
                            type="text"
                            value={perf.contract_value}
                            onChange={(e) => updatePastPerformance(index, 'contract_value', e.target.value)}
                            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                            placeholder="e.g., $2.5M"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-1">
                            Client Organization
                          </label>
                          <input
                            type="text"
                            value={perf.client}
                            onChange={(e) => updatePastPerformance(index, 'client', e.target.value)}
                            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                            placeholder="e.g., DoD/Air Force"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-1">
                            Year
                          </label>
                          <input
                            type="text"
                            value={perf.year}
                            onChange={(e) => updatePastPerformance(index, 'year', e.target.value)}
                            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                            placeholder="e.g., 2023-2024"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1">
                          Project Title
                        </label>
                        <input
                          type="text"
                          value={perf.title}
                          onChange={(e) => updatePastPerformance(index, 'title', e.target.value)}
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                          placeholder="e.g., AI/ML Platform Development for Predictive Maintenance"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1">
                          Detailed Description of Work Performed
                        </label>
                        <textarea
                          value={perf.description}
                          onChange={(e) => updatePastPerformance(index, 'description', e.target.value)}
                          rows={3}
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                          placeholder="Describe the scope, challenges, solution approach, team size, methodologies used..."
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1">
                          Technologies Used (comma-separated)
                        </label>
                        <input
                          type="text"
                          value={perf.technologies.join(', ')}
                          onChange={(e) => updatePastPerformance(index, 'technologies', e.target.value.split(',').map(t => t.trim()))}
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                          placeholder="e.g., Python, TensorFlow, AWS SageMaker, Docker, Kubernetes"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-1">
                          Key Outcomes & Achievements
                        </label>
                        <textarea
                          value={perf.outcomes}
                          onChange={(e) => updatePastPerformance(index, 'outcomes', e.target.value)}
                          rows={2}
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                          placeholder="Quantifiable results, awards received, customer satisfaction metrics..."
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}

          {/* RFP Context Tab */}
          {activeTab === 'context' && (
            <>
              <Card className="bg-gray-800 border-gray-700 p-6">
                <h2 className="text-2xl font-semibold text-white mb-6">RFP Targeting & Context</h2>

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      🎯 Target RFP Examples (Detailed)
                    </label>
                    <p className="text-sm text-gray-400 mb-2">
                      Provide detailed examples of ideal RFPs you want to pursue. Include full context, requirements, and why they align with your capabilities.
                    </p>
                    <textarea
                      value={settings.company_profile.target_rfp_examples}
                      onChange={(e) => setSettings({
                        ...settings,
                        company_profile: { ...settings.company_profile, target_rfp_examples: e.target.value }
                      })}
                      rows={10}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder={`Example 1: Enterprise AI/ML Platform Development
- Agency: Department of Defense, Air Force Research Laboratory
- Value Range: $5M-$10M
- Duration: 3-5 years
- Key Requirements: Development of scalable ML platform for predictive maintenance, real-time data processing, model training and deployment infrastructure
- Why Good Fit: Aligns with our AI/ML expertise, previous DoD work, and cleared personnel availability
- Typical Competition: Booz Allen Hamilton, SAIC, Leidos
- Win Strategy: Emphasize proprietary ML frameworks, cost-effective approach, past performance on similar AFRL contracts

Example 2: Cloud Migration and Modernization
- Agency: Department of Veterans Affairs
- Value Range: $2M-$5M
- Duration: 18-24 months
- Key Requirements: Migrate legacy applications to AWS GovCloud, implement DevOps practices, establish CI/CD pipelines
- Why Good Fit: Strong AWS partnership, successful VA modernization projects, experienced cloud architects
- Typical Competition: Accenture Federal, GDIT, CGI Federal
- Win Strategy: Highlight VA-specific experience, security clearances, agile transformation methodology`}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      📋 Technical Approach Templates
                    </label>
                    <p className="text-sm text-gray-400 mb-2">
                      Standard technical approaches and methodologies you typically propose.
                    </p>
                    <textarea
                      value={settings.company_profile.technical_approach_templates}
                      onChange={(e) => setSettings({
                        ...settings,
                        company_profile: { ...settings.company_profile, technical_approach_templates: e.target.value }
                      })}
                      rows={8}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder={`Our Standard Technical Approach:

1. Discovery & Assessment Phase (10-15% of timeline)
   - Stakeholder interviews and requirements gathering
   - Current state architecture assessment
   - Gap analysis and risk identification
   - Development of detailed project plan

2. Design & Architecture Phase (20-25% of timeline)
   - Solution architecture design
   - Technology stack selection
   - Security and compliance review
   - Proof of concept development

3. Implementation Phase (40-50% of timeline)
   - Agile/Scrum methodology with 2-week sprints
   - Continuous integration/deployment
   - Regular stakeholder demos
   - Incremental delivery of features

4. Testing & Validation Phase (15-20% of timeline)
   - Unit, integration, and system testing
   - User acceptance testing
   - Performance and security testing
   - Documentation and training

5. Deployment & Transition Phase (10-15% of timeline)
   - Production deployment
   - Knowledge transfer
   - Post-deployment support
   - Lessons learned documentation`}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      💰 Pricing Strategies
                    </label>
                    <p className="text-sm text-gray-400 mb-2">
                      Typical pricing strategies, rate structures, and cost optimization approaches.
                    </p>
                    <textarea
                      value={settings.company_profile.pricing_strategies}
                      onChange={(e) => setSettings({
                        ...settings,
                        company_profile: { ...settings.company_profile, pricing_strategies: e.target.value }
                      })}
                      rows={8}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-kamiwaza-green"
                      placeholder={`Pricing Strategy Guidelines:

Contract Types Preferred:
- Firm Fixed Price (FFP): For well-defined requirements
- Time & Materials (T&M): For evolving requirements
- Cost Plus Fixed Fee (CPFF): For R&D or high-risk projects

Labor Categories & Rates:
- Senior Technical Lead: $200-250/hr
- Software Engineer: $150-180/hr
- Data Scientist: $175-200/hr
- Project Manager: $160-190/hr
- Junior Developer: $100-130/hr

Cost Optimization Strategies:
- Blended rate approach to reduce overall costs
- Offshore/nearshore resources for non-sensitive work (20-30% cost reduction)
- Automation and tooling investments to reduce manual effort
- Reuse of existing frameworks and components

Typical Cost Breakdown:
- Labor: 65-70%
- Infrastructure/Tools: 10-15%
- Program Management: 10-12%
- Overhead & G&A: 8-10%
- Fee/Profit: 8-10%

Competitive Positioning:
- Target 15-20% below large integrator pricing
- Emphasize value through innovation and efficiency
- Flexible pricing for strategic opportunities`}
                    />
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>

        {message && (
          <div className={`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
            message.type === 'success' ? 'bg-green-600' : 'bg-red-600'
          } text-white`}>
            {message.text}
          </div>
        )}
      </div>
    </div>
  )
}