# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-26

### Added
- Repository foundation: directory structure, CI/CD, core configuration
- 6-doc enterprise planning templates (Business Case through Status)
- Inventory tracking CSVs for plugins and skills
- Single validation script (`scripts/validate.sh`)
- Developer onboarding script (`scripts/setup-dev.sh`)
- GitHub Actions CI workflow (tiered: validate + test)
- 14 standalone skills across 4 categories:
  - Search & Discovery: carrier-lookup (Free), vin-decoder (Pro), entity-mapper (Pro)
  - Safety & Compliance: safety-scorer (Free), inspection-analyzer (Pro), compliance-monitor (Pro)
  - Vetting & Risk: insurance-validator (Pro), authority-checker (Free), vetting-rules (Pro+), fraud-detector (Pro)
  - Operations: bulk-processor (SMB), data-exporter (Pro), contact-verifier (Pro), tms-connector (Enterprise)
- API discovery documentation with 11 confirmed endpoints
