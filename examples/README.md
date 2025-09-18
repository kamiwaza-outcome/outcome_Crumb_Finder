# Example Company Configurations

This directory contains example configuration files for different types of companies using the RFP Discovery System. These examples demonstrate how to configure the system for various industries and use cases.

## Available Examples

### 1. Defense Contractor (`defense_contractor_config.json`)
- **Industry**: Defense & Aerospace
- **Focus**: C4ISR systems, tactical communications, cybersecurity
- **Key Features**:
  - Security clearance requirements
  - Military standards compliance
  - Classified program experience
  - High contract values ($500K - $50M)

### 2. Software Consulting (`software_consulting_config.json`)
- **Industry**: Technology Consulting
- **Focus**: Digital transformation, cloud migration, custom development
- **Key Features**:
  - Agile methodologies
  - Cloud expertise (AWS, Azure, GCP)
  - Small business set-aside eligible
  - Mid-range contracts ($100K - $5M)

### 3. AI/ML Company (`ai_ml_company_config.json`)
- **Industry**: Artificial Intelligence & Machine Learning
- **Focus**: Enterprise AI, MLOps, intelligent automation
- **Key Features**:
  - Deep learning and NLP expertise
  - Edge AI capabilities
  - Explainable AI focus
  - Data science team

## How to Use These Examples

1. **Choose the closest match**: Select the example that best matches your company's profile
2. **Copy to root directory**:
   ```bash
   cp examples/ai_ml_company_config.json company_config.json
   ```
3. **Customize the configuration**:
   - Update company name and profile
   - Modify capabilities to match your expertise
   - Adjust keywords and NAICS codes
   - Update contract value ranges
   - Add your past performance examples

## Configuration Structure

Each configuration file contains:

### Company Section
- Basic company information (name, website, industry)
- Company profile and description
- High-level capabilities list

### Capabilities Section
- Core capabilities and services
- Technical expertise (languages, tools, platforms)
- Certifications and compliance
- Unique differentiators

### RFP Targeting Section
- Search keywords for finding relevant RFPs
- NAICS codes for your industry
- Set-aside eligibility (Small Business, 8(a), etc.)
- Contract vehicles you hold

### Scoring Criteria Section
- Must-have keywords for high relevance
- Red flag keywords to avoid
- Contract value preferences
- Duration preferences
- Geographic preferences

### Past Performance Section
- Examples of winning RFPs
- Case studies demonstrating success
- Key technologies used

### AI Evaluation Prompts
- Company strengths summary
- Description of ideal opportunity
- Evaluation focus areas for AI scoring

## Tips for Customization

1. **Be Specific**: The more specific your keywords and capabilities, the better the AI can identify relevant opportunities

2. **Include Past Wins**: Add real examples of RFPs you've won to help the AI understand your success patterns

3. **Set Realistic Ranges**: Configure contract values and durations based on your actual capacity

4. **Update Regularly**: Refresh your configuration as your capabilities and focus areas evolve

5. **Test Incrementally**: Start with broader keywords and narrow down based on results

## Running the Setup Script

Instead of manually editing these files, you can use the interactive setup script:

```bash
python setup_company.py
```

This will guide you through creating a customized configuration for your company.

## Need Help?

If you need assistance customizing these configurations:
1. Review the main README.md for system documentation
2. Check the setup guide in docs/
3. Run the setup script for guided configuration
4. Test with limited searches first (`python main.py --test`)