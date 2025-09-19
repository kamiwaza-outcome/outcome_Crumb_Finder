# 🎯 Crumb Finder - Enterprise RFP Intelligence Platform

[![Daily RFP Discovery](https://github.com/finnegannorris/Crumb_finder/actions/workflows/daily-rfp-discovery.yml/badge.svg)](https://github.com/finnegannorris/Crumb_finder/actions/workflows/daily-rfp-discovery.yml)
[![Weekly RFP Obituary](https://github.com/finnegannorris/Crumb_finder/actions/workflows/weekly-rfp-obituary.yml/badge.svg)](https://github.com/finnegannorris/Crumb_finder/actions/workflows/weekly-rfp-obituary.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenAI GPT-5](https://img.shields.io/badge/AI-GPT--5-green.svg)](https://openai.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

**Revolutionize your government contracting pipeline with AI-powered RFP discovery.**

Crumb Finder is an enterprise-grade intelligence platform that automates the complete government contracting opportunity lifecycle. Built for technology companies pursuing federal contracts, it processes thousands of RFPs daily using advanced two-phase AI screening with GPT-5, delivering qualified opportunities directly to your team while maintaining complete audit trails.

## 🚀 Why Crumb Finder?

**Never miss another opportunity.** Traditional RFP discovery methods capture only 10-20% of relevant opportunities. Crumb Finder's OVERKILL mode processes every single RFP posted to SAM.gov—over 2000 daily—ensuring complete market coverage.

**AI that understands your business.** Our two-phase screening system combines GPT-5-mini rapid filtering with GPT-5 deep analysis, learning from your company profile and past wins to deliver increasingly accurate opportunity scoring.

**Production-ready automation.** With 99.9% uptime, 530+ concurrent AI analyses, and automatic lifecycle management, Crumb Finder integrates seamlessly into your business development workflow.

## ✨ Core Capabilities

### 🧠 Advanced AI Analysis Engine
- **Two-Phase Screening**: GPT-5-mini eliminates 70-80% of irrelevant RFPs, GPT-5 provides deep analysis
- **Ultra-High Concurrency**: 530+ simultaneous analyses (400 mini + 130 deep)
- **Smart Scoring**: 10-point scale with color-coded prioritization and strategic recommendations
- **Context-Aware**: Learns from your company profile, capabilities, and past winning proposals

### 🔥 OVERKILL Mode - Complete Market Coverage
- **Process ALL RFPs**: No filters, no limits—every SAM.gov posting analyzed
- **20,000+ Daily Capacity**: Handle the busiest government contracting days
- **Weekend Intelligence**: Automatic multi-day catchup for comprehensive coverage
- **Zero Missed Opportunities**: The only system that guarantees complete market surveillance

### 📊 Intelligent Organization
- **Three-Tier System**: Qualified (7-10), Maybe (4-6), Complete Audit Trail (all scores)
- **Lifecycle Management**: Automatic status tracking from discovery to completion/expiration
- **Document Integration**: 50 attachments per RFP with organized Google Drive storage
- **Smart Archival**: Expired → Graveyard, Completed → Success Bank

### ☠️ RFP Obituary System
- **Weekly Memorials**: AI-generated humorous obituaries for expired high-value opportunities
- **Learning Tool**: Understand missed opportunities with strategic insights
- **Team Engagement**: Friday 5PM ET delivery keeps your team informed and entertained

## 🎮 Quick Start

```bash
# Clone and install
git clone https://github.com/[your-username]/Crumb_Finder.git
cd Crumb_Finder
pip install -r requirements.txt

# OVERKILL mode - Process ALL RFPs
python scripts/working_overkill.py --date 09/13/2025 --max 20000

# Standard discovery with filters
python scripts/enhanced_discovery.py

# Test mode (20 RFPs)
python main.py --test
```

**📋 [Complete Setup Guide →](/docs/SETUP.md)** - Detailed configuration for your company

## 📊 Performance at Scale

- **Daily Capacity**: 20,000+ RFPs processed
- **Processing Speed**: ~1000 RFPs/hour in OVERKILL mode
- **Concurrent AI Analyses**: 530+ simultaneous threads
- **Success Rate**: 99.9% with automatic retry and recovery
- **Market Coverage**: 100% of SAM.gov opportunities

## 🏗️ Technical Architecture

### System Architecture
```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions                         │
│         Daily 5AM ET + Manual Triggers                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    SAM.gov API                          │
│     • 20+ NAICS Codes  • 40+ PSC Codes                  │
│     • 100+ AI Keywords • Date Range Search              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Deduplication Engine                       │
│     • Notice ID Matching • Fuzzy Title Matching         │
│     • Cross-Sheet Detection • 30min Cache               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│           Two-Phase AI Processing                       │
│                                                          │
│  Phase 1: GPT-5-mini Screening (400 concurrent)         │
│  ├── Rapid filtering with adaptive thresholds           │
│  ├── 4M TPM capacity utilization                        │
│  └── 70-80% noise reduction                            │
│                                                          │
│  Phase 2: GPT-5 Deep Analysis (130 concurrent)          │
│  ├── Comprehensive scoring and justification            │
│  ├── 2M TPM capacity utilization                        │
│  └── Context-aware strategic recommendations            │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐ ┌───────▼──────┐ ┌──────▼───────┐
│  Qualified   │ │    Maybe     │ │     All      │
│   (7-10)     │ │    (4-6)     │ │   (1-10)     │
│              │ │              │ │              │
│ Main Sheet + │ │ Maybe Sheet  │ │ Spam Sheet   │
│ Drive Docs   │ │              │ │              │
└──────┬───────┘ └──────────────┘ └──────────────┘
       │
┌──────▼───────────────────────────────────────────┐
│        Storage & Notifications                   │
│  • Google Drive: Folders + 50 Attachments        │
│  • Google Sheets: Data + Status + Colors         │
│  • Slack: Rich notifications + Obituaries        │
└──────────────────────────────────────────────────┘
```

### Core Modules

#### Data Layer (`src/`)
- **`sam_client.py`**: SAM.gov API client with retry logic
- **`ai_qualifier.py`**: GPT-5 analysis engine with circuit breakers
- **`sheets_manager.py`**: Google Sheets operations and formatting
- **`drive_manager.py`**: Document storage and attachment handling
- **`slack_notifier.py`**: Rich notification system
- **`deduplication.py`**: Advanced duplicate detection

#### Processing Engines (`archive/`)
- **`parallel_processor.py`**: GPT-5 deep analysis pipeline
- **`parallel_mini_processor.py`**: GPT-5-mini screening engine

#### Automation (`scripts/`)
- **`working_overkill.py`**: OVERKILL mode processor
- **`enhanced_discovery.py`**: Three-tier discovery
- **`import_rfp.py`**: Manual RFP import
- **`rfp_obituary.py`**: Weekly obituary generator
- **40+ additional scripts** for maintenance and utilities

## 🎮 Usage Examples

### Daily Operations
```bash
# Automated discovery (GitHub Actions: 5AM ET, Tue-Sat)
# OVERKILL mode processes all RFPs automatically

# Manual operations
python scripts/working_overkill.py --date 09/13/2025 --max 20000
python scripts/enhanced_discovery.py --days-back 3
python scripts/rfp_obituary.py --days 7
```

### Import & Maintenance
```bash
# Import specific RFP
python scripts/import_rfp.py https://sam.gov/opp/{noticeId}/view

# System maintenance
python utilities/daily_sheet_maintenance.py
python scripts/download_todays_attachments.py
```

## 🗂️ Project Structure

```
Crumb_finder/
├── scripts/              # 40+ execution scripts
│   ├── working_overkill.py      # OVERKILL processor
│   ├── enhanced_discovery.py    # Three-tier discovery
│   ├── import_rfp.py           # Manual import
│   ├── rfp_obituary.py         # Obituary generator
│   └── [36+ more scripts]      # Various utilities
├── src/                 # Core modules
│   ├── sam_client.py           # SAM.gov API
│   ├── ai_qualifier.py         # GPT-5 analysis
│   ├── sheets_manager.py       # Google Sheets
│   ├── drive_manager.py        # Google Drive
│   ├── slack_notifier.py       # Slack integration
│   └── deduplication.py        # Duplicate detection
├── archive/             # Processing engines
│   ├── parallel_processor.py   # Deep analysis
│   └── parallel_mini_processor.py # Screening
├── utilities/           # Maintenance tools
│   ├── sheet_organizer.py      # Sheet formatting
│   ├── daily_sheet_maintenance.py # Status updates
│   └── weekend_catchup.py      # Weekend processing
├── data/                # Data files
│   └── winning_rfps.txt        # Past wins context
├── .github/workflows/   # GitHub Actions
│   ├── daily-rfp-discovery.yml # Daily automation
│   ├── weekly-rfp-obituary.yml # Weekly obituaries
│   └── import-rfp.yml          # Manual imports
└── config.py            # System configuration
```

