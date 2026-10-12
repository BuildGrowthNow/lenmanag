# Agent Rules — LenManag / LenQuant Platform

## Site Adjustments

**Never create one-off scripts to patch sites directly.**

Do not write standalone Python or shell scripts that:
- Modify S3 CSS files directly
- Update MongoDB `generated_sites` records by hand
- Upload or overwrite site assets outside the platform

Instead, use the platform's API endpoints and generation system to make any site improvements. The platform can handle adjustments on specific sites without going offline — scripts bypass platform logic, leave no audit trail, and must be deleted after use anyway.

## Parallelism

Work sequentially. Do not spawn sub-agents or run parallel tool calls that hit the LLM. AWS Bedrock has strict requests-per-minute limits; parallel tasks cause rate-limit errors.

## General

Follow all rules in `CLAUDE.md`. These agent-specific rules supplement, not replace, the main guide.
