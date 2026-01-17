# Arena Cloud - Implementation Plan

## Executive Summary

**Strategic Position:** Arena is to Arena Cloud what Git is to GitHub.

**Goal:** Build Arena Cloud as an optional, value-added layer on top of local-first Arena CLI, following the proven Git/GitHub mental model.

**Core Principle:** Local Arena works perfectly offline forever. Arena Cloud adds collaboration, analytics, and scale when users need it.

---

## The Git/GitHub Analogy

### Arena (Local) = Git

**What it is:**
- Local-first CLI tool
- Runs on user's machine
- No account required
- Open-core architecture

**What it does:**
- Analyze video
- Transcribe audio
- Detect interesting moments
- Validate standalone context
- Generate clips locally
- Export files + metadata

**Value Proposition:**
- Control
- Privacy
- Speed
- Trust
- Ownership

### Arena Cloud = GitHub

**What it is:**
- Hosted service on top of Arena
- Requires account (OAuth + email/password)
- Optional, not mandatory

**What it does:**
- Sync metadata (NOT raw video)
- Analytics across platforms
- Track clip performance
- Team collaboration
- Remote AI compute (optional)
- Automation pipelines

**Value Proposition:**
- Convenience
- Scale
- Leverage
- Business intelligence
- Collaboration

---

## Current Architecture (Baseline)

### Tech Stack
- **CLI:** Node.js 18+ TypeScript (`/cli/`)
- **Engine:** Python 3.9+ (`/engine/`)
- **Communication:** Subprocess bridge via JSON over stdout
- **Config:** `~/.arena/config.json` (plain text)
- **Output:** `.arena/output/` (local directory structure)

### Current Workflow
```bash
# 1. Local processing (no auth, no cloud)
arena process video.mp4 -c 5

# 2. Outputs to .arena/output/
.arena/output/
├── clips/
│   ├── clip_001.mp4
│   ├── clip_001_thumb.jpg
│   └── clip_001_metadata.json
└── analysis_results.json
```

### What Works Today
✅ Full video processing offline
✅ 4-layer editorial system
✅ Hybrid audio-visual analysis
✅ Professional clip alignment
✅ Complete metadata export

### What's Missing
❌ No cross-video insights
❌ No platform analytics
❌ No team collaboration
❌ No sync across devices
❌ No remote compute option

---

## Phase 1: Arena Cloud Foundation

### Goals
1. ✅ Maintain local Arena as primary workflow (no regression)
2. ✅ Add `arena cloud` command namespace (clean separation)
3. ✅ Authentication for cloud features only
4. ✅ Metadata sync (NOT video upload unless user chooses)
5. ✅ Basic analytics dashboard (web)
6. ✅ Cloud backend infrastructure (FastAPI + Supabase)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Arena CLI (Local First)                    │
│                                                              │
│  Local Commands (NO AUTH REQUIRED):                         │
│  • arena process video.mp4                                   │
│  • arena analyze video.mp4                                   │
│  • arena clip video.mp4                                      │
│                                                              │
│  Cloud Commands (AUTH REQUIRED):                             │
│  • arena cloud login                                         │
│  • arena cloud sync                                          │
│  • arena cloud analytics                                     │
│  • arena cloud process (optional remote compute)             │
│  • arena cloud team                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
                  Metadata Sync Only
                  (via HTTPS REST API)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Arena Cloud Backend                       │
│                                                              │
│  Tech Stack:                                                 │
│  • FastAPI (Python 3.11+)                                    │
│  • Supabase (Auth + PostgreSQL + Storage)                    │
│  • Redis (caching, job queue)                                │
│  • Celery (async task processing)                            │
│                                                              │
│  Features:                                                   │
│  • REST API for metadata sync                                │
│  • Analytics aggregation                                     │
│  • Team management                                           │
│  • Optional: Remote AI compute                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
                     PostgreSQL
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                      Data Model                              │
│                                                              │
│  Tables:                                                     │
│  • users (email, auth_id, created_at)                        │
│  • videos (user_id, title, metadata_json, created_at)        │
│  • clips (video_id, clip_metadata, performance_data)         │
│  • teams (name, owner_id)                                    │
│  • team_members (team_id, user_id, role)                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Command Examples

### Local Arena (No Auth)
```bash
# Everything works offline, no account needed
arena process video.mp4 -c 5
arena process video.mp4 --use-4layer -c 10
arena analyze video.mp4
```

### Arena Cloud (Requires Auth)
```bash
# 1. Authenticate once
arena cloud login --provider github

# 2. Sync local videos to cloud (metadata only)
arena cloud sync

# 3. View analytics
arena cloud analytics

# 4. View specific video analytics
arena cloud analytics -v abc123

# 5. Create team
arena cloud team create "My Team"

# 6. Invite team member
arena cloud team invite my-team user@example.com --role member

# 7. Process video on cloud (optional, costs money)
arena cloud process video.mp4 -c 5 --remote

# 8. Logout
arena cloud logout
```

---

## Data Privacy & Trust

### What Gets Uploaded to Cloud?

**Uploaded (Metadata Only):**
- Video title, duration
- Clip timestamps, titles, scores
- Analysis results (interest scores, content types)
- Thumbnail images (optional)

**NOT Uploaded (Stays Local):**
- Raw video files
- Raw audio files
- Transcripts (unless user opts in)
- Personal information

**User Controls:**
- `arena cloud sync --dry-run` - See what would be uploaded
- `arena config set cloud.sync.auto false` - Disable auto-sync
- `arena cloud delete video-id` - Delete from cloud

---

## Implementation Timeline

### Week 1-2: Backend Foundation
- [ ] Set up Supabase project
- [ ] Define database schema
- [ ] Implement FastAPI backend
- [ ] Create REST API endpoints
- [ ] Deploy to Railway/Render

### Week 3: CLI Cloud Commands
- [ ] Implement AuthManager
- [ ] Create cloud command namespace
- [ ] Implement `arena cloud login`
- [ ] Implement `arena cloud sync`
- [ ] Implement `arena cloud analytics`
- [ ] Test end-to-end flow

### Week 4: Web Dashboard MVP
- [ ] Set up React + Vite project
- [ ] Implement login page
- [ ] Implement video list
- [ ] Implement video detail with analytics
- [ ] Deploy to Vercel

### Week 5: Polish & Launch
- [ ] Documentation
- [ ] Error handling improvements
- [ ] User onboarding flow
- [ ] Soft launch to beta users

**Total: 5 weeks for MVP**

---

## Pricing Model (Future)

### Free Tier (Local Arena)
- ✅ Unlimited local processing
- ✅ All 4-layer editorial features
- ✅ Full control and privacy
- ❌ No cloud sync
- ❌ No analytics
- ❌ No team collaboration

### Cloud Basic ($9/month)
- ✅ All free tier features
- ✅ Cloud metadata sync
- ✅ Basic analytics dashboard
- ✅ Up to 50 videos synced
- ✅ 1 team (up to 3 members)
- ❌ No remote compute

### Cloud Pro ($29/month)
- ✅ All Basic features
- ✅ Unlimited video sync
- ✅ Advanced analytics
- ✅ Multiple teams
- ✅ Remote compute credits ($10/month)
- ✅ API access

### Cloud Enterprise (Custom)
- ✅ All Pro features
- ✅ Dedicated compute
- ✅ Custom integrations
- ✅ SSO
- ✅ Priority support

---

## Recommendation

**Start with:**
1. **CLI Cloud Commands Only** (Weeks 1-3)
   - Backend + Auth + Sync + Analytics
   - No web dashboard yet
   - Email auth only (no OAuth complexity)

2. **Test with Beta Users**
   - Get feedback on CLI experience
   - Validate data model
   - Refine sync workflow

3. **Add Web Dashboard Later** (Week 4+)
   - After CLI is solid
   - Based on user feedback
   - Start simple (video list + basic charts)

**This gets you:**
- ✅ Fastest path to usable MVP
- ✅ Validates core value prop (analytics without video upload)
- ✅ Can iterate based on real usage
- ✅ Maintains trust with local-first approach

---

For full implementation details, database schema, and code examples, see the complete plan in `.claude/plans/ethereal-prancing-shamir.md`.
