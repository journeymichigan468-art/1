# Remote Desktop Protocol Project

## Overview
This project is a GitHub-imported repository containing GitHub Actions workflows for creating temporary Windows 11 virtual machines with remote desktop access.

**Important:** The actual RDP functionality runs on GitHub Actions, not on Replit. This Replit project serves as an informational landing page explaining how to use the GitHub workflows.

## Project Structure
- `.github/workflows/` - GitHub Actions workflow YAML files
  - `rdp-tailscale-rustdesk-A.yml` - Main workflow for creating Windows VMs
  - `rdp-tailscale-rustdesk-B.yml` - Handoff workflow for continuity
  - `rdp-tailscale-stop.yml` - Cleanup workflow
  - `blank.yml` - Basic CI workflow
- `public/` - Static web assets
  - `index.html` - Informational landing page
  - `styles.css` - Page styling
- `server.js` - Express.js server serving the landing page

## Tech Stack
- Node.js with Express.js
- Static HTML/CSS frontend

## Running the Project
The server runs on port 5000 and serves the informational landing page. The actual RDP functionality requires:
1. Fork the repository on GitHub
2. Go to the Actions tab
3. Run a workflow with Tailscale credentials

## Recent Changes
- Feb 2026: Created informational landing page for Replit environment
