'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/loading-spinner'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { toast } from '@/components/ui/toast'

interface RFPOpportunity {
  notice_id: string
  title: string
  agency: string
  description: string
  posted_date: string
  response_deadline: string | null
  url: string
}

interface RFPAssessment {
  is_qualified: boolean
  qualification_level: 'qualified' | 'maybe' | 'rejected'
  relevance_score: number
  justification: string
  key_requirements: string[]
  company_advantages: string[]
  suggested_approach: string
}

interface ProcessedRFP {
  opportunity: RFPOpportunity
  assessment: RFPAssessment
  drive_folder_url?: string
}

export function RFPTable() {
  const [rfps, setRfps] = useState<ProcessedRFP[]>([])
  const [filter, setFilter] = useState<'all' | 'qualified' | 'maybe' | 'rejected'>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [selectedRFP, setSelectedRFP] = useState<ProcessedRFP | null>(null)

  useEffect(() => {
    loadRFPs()
  }, [filter])

  const loadRFPs = async () => {
    try {
      setIsLoading(true)
      const params = filter === 'all' ? {} : { qualification_level: filter }
      const response = await api.get('/rfp/recent', { params })
      setRfps(response.data || [])
    } catch (error) {
      console.error('Failed to load RFPs:', error)
      toast.error('Failed to load RFPs')
    } finally {
      setIsLoading(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 7) return 'text-green-500'
    if (score >= 4) return 'text-yellow-500'
    return 'text-red-500'
  }

  const getQualificationBadge = (level: string) => {
    switch (level) {
      case 'qualified':
        return (
          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-900 text-green-300">
            QUALIFIED
          </span>
        )
      case 'maybe':
        return (
          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-900 text-yellow-300">
            MAYBE
          </span>
        )
      case 'rejected':
        return (
          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-900 text-red-300">
            REJECTED
          </span>
        )
      default:
        return null
    }
  }

  return (
    <>
      <Card className="bg-gray-800 border-gray-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Discovered RFPs</h2>
          <div className="flex gap-2">
            {(['all', 'qualified', 'maybe', 'rejected'] as const).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={filter === f ? 'default' : 'outline'}
                onClick={() => setFilter(f)}
                className={
                  filter === f
                    ? 'bg-kamiwaza-green hover:bg-kamiwaza-green-dark'
                    : 'border-gray-600 text-gray-400 hover:text-white'
                }
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        ) : rfps.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            No RFPs found. Run a discovery to find opportunities.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400">Score</th>
                  <th className="text-left py-3 px-4 text-gray-400">Title</th>
                  <th className="text-left py-3 px-4 text-gray-400">Agency</th>
                  <th className="text-left py-3 px-4 text-gray-400">Posted</th>
                  <th className="text-left py-3 px-4 text-gray-400">Deadline</th>
                  <th className="text-left py-3 px-4 text-gray-400">Status</th>
                  <th className="text-left py-3 px-4 text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rfps.map((rfp) => (
                  <tr
                    key={rfp.opportunity.notice_id}
                    className="border-b border-gray-700 hover:bg-gray-900 transition-colors cursor-pointer"
                    onClick={() => setSelectedRFP(rfp)}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-2xl font-bold ${getScoreColor(
                            rfp.assessment.relevance_score
                          )}`}
                        >
                          {rfp.assessment.relevance_score}
                        </span>
                        <span className="text-gray-500">/10</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="text-white font-medium line-clamp-2">
                          {rfp.opportunity.title}
                        </p>
                        <p className="text-gray-500 text-xs mt-1">
                          {rfp.opportunity.notice_id}
                        </p>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-300 max-w-xs truncate">
                      {rfp.opportunity.agency}
                    </td>
                    <td className="py-3 px-4 text-gray-400">
                      {new Date(rfp.opportunity.posted_date).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      {rfp.opportunity.response_deadline ? (
                        <span className="text-gray-300">
                          {new Date(rfp.opportunity.response_deadline).toLocaleDateString()}
                        </span>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {getQualificationBadge(rfp.assessment.qualification_level)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-kamiwaza-blue hover:text-kamiwaza-blue-light"
                          onClick={() => window.open(rfp.opportunity.url, '_blank')}
                        >
                          SAM.gov
                        </Button>
                        {rfp.drive_folder_url && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-green-500 hover:text-green-400"
                            onClick={() => window.open(rfp.drive_folder_url, '_blank')}
                          >
                            Drive
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* RFP Details Modal */}
      {selectedRFP && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setSelectedRFP(null)}
        >
          <div
            className="bg-gray-800 rounded-lg p-6 max-w-4xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-white">
                  {selectedRFP.opportunity.title}
                </h3>
                <p className="text-gray-400 mt-1">{selectedRFP.opportunity.agency}</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-sm text-gray-400">Relevance Score</p>
                  <p className={`text-3xl font-bold ${getScoreColor(selectedRFP.assessment.relevance_score)}`}>
                    {selectedRFP.assessment.relevance_score}/10
                  </p>
                </div>
                {getQualificationBadge(selectedRFP.assessment.qualification_level)}
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold text-gray-400 mb-2">Assessment</h4>
                <p className="text-gray-300">{selectedRFP.assessment.justification}</p>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-gray-400 mb-2">Key Requirements</h4>
                <ul className="list-disc list-inside text-gray-300">
                  {selectedRFP.assessment.key_requirements.map((req, i) => (
                    <li key={i}>{req}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-gray-400 mb-2">Company Advantages</h4>
                <ul className="list-disc list-inside text-gray-300">
                  {selectedRFP.assessment.company_advantages.map((adv, i) => (
                    <li key={i}>{adv}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-gray-400 mb-2">Suggested Approach</h4>
                <p className="text-gray-300">{selectedRFP.assessment.suggested_approach}</p>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-gray-400 mb-2">Description</h4>
                <p className="text-gray-300 text-sm max-h-40 overflow-y-auto">
                  {selectedRFP.opportunity.description}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Posted:</span>{' '}
                  <span className="text-gray-300">
                    {new Date(selectedRFP.opportunity.posted_date).toLocaleDateString()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Deadline:</span>{' '}
                  <span className="text-gray-300">
                    {selectedRFP.opportunity.response_deadline
                      ? new Date(selectedRFP.opportunity.response_deadline).toLocaleDateString()
                      : 'Not specified'}
                  </span>
                </div>
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-700">
                <Button
                  onClick={() => window.open(selectedRFP.opportunity.url, '_blank')}
                  className="bg-kamiwaza-blue hover:bg-kamiwaza-blue-dark"
                >
                  View on SAM.gov
                </Button>
                {selectedRFP.drive_folder_url && (
                  <Button
                    onClick={() => window.open(selectedRFP.drive_folder_url, '_blank')}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    View in Google Drive
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => setSelectedRFP(null)}
                  className="ml-auto"
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}