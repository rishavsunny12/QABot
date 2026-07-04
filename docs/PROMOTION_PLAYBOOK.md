# AutoQA Agent — Promotion Playbook

Open-source launch and growth guide for [QABot](https://github.com/rishavsunny12/QABot) (AutoQA Agent v1.0).

Use this as a checklist and copy source. Adapt tone to each community; never paste the same wall of text everywhere.

---

## 1. Positioning (say this consistently)

**One-liner:**  
Open-source platform that crawls your web app, maps user flows, generates Playwright tests, runs them on a schedule, and suggests selector fixes when UI changes break tests.

**Who it’s for:**
- Solo devs and small teams without a dedicated QA org
- Engineers migrating from manual QA or flaky record-and-playback tools
- Teams already on Playwright who want discovery + maintenance help

**Why now (v1 OSS):**
- Self-host with Docker Compose — no SaaS lock-in
- MIT license
- Billing deferred to v2 — experiment freely on localhost or private networks

**Honest caveat (builds trust):**  
MVP for local/private use. Not production-hardened out of the box. Say this upfront on Reddit and HN; it reduces backlash and attracts the right contributors.

**Differentiators vs. alternatives:**

| You might use… | AutoQA Agent adds… |
|----------------|-------------------|
| Raw Playwright | Crawl → flow map → generated specs |
| Cypress Dashboard | Self-hosted, Playwright-native, AI healing suggestions |
| Testim / Mabl | OSS, you own artifacts and infra |
| Only CI scripts | Visual regression, schedules, team roles, browser farm |

---

## 2. Assets to prepare once (reuse everywhere)

Create these before heavy promotion:

1. **60–90s demo GIF or video** — TodoMVC walkthrough from README (login → crawl → flow map → run → failure + healing). No voice required; captions are enough.
2. **3 screenshots** — Flow map (React Flow), run history with AI summary, visual diff view.
3. **GitHub Release v1.0.0** — Tag exists; add release notes + GIF embed.
4. **“Good first issue” labels** — 3–5 small tasks for drive-by contributors.
5. **Comparison table** in README (optional) — “When to use AutoQA vs. plain Playwright.”

Repo hygiene (GitHub discovery):
- Topics: `playwright`, `testing`, `qa`, `test-automation`, `fastapi`, `nextjs`, `open-source`, `visual-regression`, `celery`
- Pin README quick start above the fold (already done)
- Add a **Sponsor** or **Discussions** tab when ready — Discussions beats Issues for “how do I…?” questions

---

## 3. Reddit strategy

Reddit rewards **specific problems solved**, not “I built a thing.” Lead with the pain, show the demo, link GitHub once.

### High-fit subreddits

| Subreddit | Angle | Post type |
|-----------|--------|-----------|
| r/playwright | Generated specs + parallel farm | Tutorial + repo link |
| r/QualityAssurance | Discovery crawl + visual regression | “Tooling Tuesday” style |
| r/webdev | Selector healing when redesigns break tests | Story + GIF |
| r/selfhosted | Docker Compose stack, MIT, no billing | Self-host guide |
| r/devops | Celery workers, scheduled runs, CI-friendly | Architecture post |
| r/SideProject | OSS v1 journey, phases 2–7 | Build log |
| r/opensource | MIT release, looking for contributors | Release announcement |
| r/programming | Only if you have a **strong** demo; high bar | Show HN-style post |
| r/ExperiencedDevs | “How we infer flows from crawl graphs” | Technical deep dive |

### Reddit rules (critical)

- **Read each sub’s rules** before posting. Many ban pure self-promo without participation history.
- **9:1 rule:** For every promo post, leave ~9 genuine comments on others’ threads in that sub (not on the same day you launch).
- **No cross-post spam** — rewrite title and opening paragraph per sub.
- **Reply to every comment** in the first 24 hours.
- **Flair correctly** (Showcase, Tool, Discussion).
- If a mod removes the post, **do not repost** — message mods or post in weekly thread if one exists.

### Ready-to-use Reddit posts

**A) r/playwright — “Generate Playwright specs from a crawl graph”**

```
Title: I open-sourced a tool that crawls your app and generates Playwright tests from inferred flows

I've been tired of maintaining selectors after every UI tweak, so I built AutoQA Agent (MIT, self-hosted).

What it does:
- BFS crawl with domain allowlist (Playwright)
- Rule-based flow inference (login, nav, CRUD, logout)
- Exports .spec.ts you can edit or run in CI
- When selectors drift, it ranks alternatives from crawl history — you approve before anything changes

Stack: FastAPI + Celery + Next.js dashboard. `docker compose up` for local demo on TodoMVC.

It's an MVP — meant for local/private networks, not public prod without hardening.

Repo: https://github.com/rishavsunny12/QABot
Demo path in README takes ~5 min. Would love feedback from people running Playwright at scale.
```

**B) r/selfhosted — “Self-hosted QA platform”**

```
Title: Self-hosted test discovery + Playwright runner (Docker Compose, MIT, no SaaS)

AutoQA Agent v1.0 — crawl a web app, map flows, generate/run Playwright tests, visual regression, scheduled runs.

Why self-hosters might care:
- Full stack in docker-compose (Postgres, Redis, workers)
- Artifacts on disk (screenshots, traces)
- OIDC SSO + team roles if you expose it internally
- Billing code exists but disabled in v1

Caveat: README documents security steps before exposing beyond localhost (rotate secrets, drop Adminer, TLS, etc.).

https://github.com/rishavsunny12/QABot — feedback on compose ergonomics welcome.
```

**C) r/QualityAssurance — problem-first**

```
Title: How do you keep E2E tests updated when the UI changes every sprint?

We built an OSS approach: crawl the app once, infer flows, generate Playwright tests, then when a run fails, get ranked selector alternatives with an explicit approve/reject step (no silent auto-healing).

Also: visual regression + scheduled runs + parallel workers.

Not trying to replace your test strategy — more like bootstrap + maintenance assist for small teams.

Open source (MIT): https://github.com/rishavsunny12/QABot

How are you handling selector maintenance today — manual, vendor tool, or letting tests rot?
```

**D) Comment template (when relevant threads appear)**

```
We ran into the same thing — maintenance cost dominated writing tests. I ended up open-sourcing a crawl → flow map → Playwright generator with optional healing suggestions (self-hosted, MIT). Happy to share architecture notes if useful: [link]. Not affiliated with any vendor; still rough around the edges for prod internet exposure.
```

### Reddit launch timing

- Post **Tuesday–Thursday, 9–11am US Eastern** for dev subs.
- One sub per day max for the first week.
- Stagger: Playwright → selfhosted → QA → opensource.

---

## 4. GitHub strategy

GitHub is your **canonical home**; other platforms funnel here.

### Release & discoverability

- [ ] Publish **GitHub Release** for `v1.0.0` with changelog + demo GIF
- [ ] Enable **GitHub Discussions** (Categories: Announcements, Q&A, Ideas, Show and tell)
- [ ] Add repository **topics** (see §2)
- [ ] Create **3 “good first issue”** items (docs, small UI, test coverage)
- [ ] Add **CONTRIBUTING.md** (short: how to run tests, PR flow)
- [ ] Star/watch your own repo from a personal account only if you actually use it — don’t astroturf

### Content on GitHub

- **Release notes** = mini blog post (problem, demo, roadmap v2)
- **Discussion post:** “Show and tell: 5-minute TodoMVC demo”
- **Issue templates:** Bug report + feature request (reduces noise)

### GitHub trending (organic)

Trending favors **velocity + stars from diverse referrers** in a short window:

1. Coordinate launch: HN + Reddit + Dev.to within 48h (not same hour — spread traffic)
2. Ask contributors/friends to **try the quick start** and star only if they genuinely use it
3. Avoid star-for-star rings — GitHub detects abuse

### Awesome lists (high ROI, low spam)

Open PRs to add AutoQA under Testing / Playwright sections:

- `awesome-playwright`
- `awesome-testing`
- `awesome-selfhosted` (if you emphasize Docker stack)

PR title example: `Add AutoQA Agent — OSS crawl-to-Playwright platform`

One-line entry:
```
- [AutoQA Agent](https://github.com/rishavsunny12/QABot) — Self-hosted crawl, flow inference, Playwright generation, visual regression, selector healing (MIT).
```

---

## 5. Hacker News (Show HN)

HN loves **technical honesty + working demo**.

**Title options:**
- Show HN: AutoQA Agent – open-source crawl-to-Playwright test platform
- Show HN: Self-hosted tool that maps user flows and generates Playwright tests

**Post body:**

```
AutoQA Agent crawls a web app (domain-restricted BFS), infers flows with rule-based heuristics, generates Playwright specs, and runs them via Celery workers. Failures can include AI-generated summaries; selector drift produces ranked alternatives that require explicit approval before updating specs.

v1.0 is MIT and self-hosted via Docker Compose. Visual regression, scheduled runs, parallel browser farm, and OIDC team roles are included. Billing is intentionally off in v1.

It's an MVP — README calls out security steps before internet exposure. I'm looking for feedback on flow inference quality and whether generated specs are useful in real codebases.

Quick start: clone, docker compose up, TodoMVC demo in README (~5 min).

https://github.com/rishavsunny12/QABot
```

**HN etiquette:** Post once. Reply substantively. No “please upvote.” Expect sharp security questions — point to self-hosting notes.

**Best time:** Weekday morning US (7–9am PT).

---

## 6. Other platforms

### Dev.to / Hashnode

Write one long post (canonical on Dev.to, cross-link on Hashnode):

**Title:** “From zero E2E tests to a generated Playwright suite in one Docker Compose stack”

Structure: Problem → architecture diagram (from README) → 5-minute demo steps → healing flow → limitations → CTA to GitHub.

Tag: `#opensource` `#playwright` `#testing` `#devops`

### LinkedIn

Audience: engineering managers, QA leads.

Post format: 5 short paragraphs + screenshot + “link in comments” (algorithm-friendly).

Focus: **maintenance cost of E2E**, not feature laundry list.

### X (Twitter)

Thread skeleton (7 tweets):

1. Hook: “Most teams don’t lack tests — they lack tests that survive the next redesign.”
2. What AutoQA does in one sentence
3. GIF: flow map
4. GIF: run + AI summary
5. Self-host, MIT, v1 no billing
6. Honest MVP caveat
7. GitHub link + “what would you want in v2?”

Pin the thread. Quote-tweet with lessons learned weekly.

### YouTube / PeerTube

**Title:** “AutoQA Agent in 5 minutes — crawl to Playwright tests (self-hosted)”

Chapters: Setup → Crawl → Generate → Run → Healing. Description links to GitHub + timestamps.

### Discord / Slack communities

Ask permission in admin channels first. Share in:

- Playwright Discord `#showcase`
- Self-hosted homelab servers (follow their promo rules)
- Local meetup Slacks

Message:

```
Built an MIT self-hosted tool that crawls apps and generates Playwright tests — looking for people to break the TodoMVC path and tell me what's confusing. GitHub: [link]. Not selling anything in v1.
```

### Product Hunt (optional)

Better after you have a polished GIF, logo, and 10+ genuine GitHub stars. Position as “Developer Tools” + “Open Source.” Prepare maker comment with roadmap.

### Newsletter sponsorships (later)

Target: Playwright Weekly, Self-Hosted Newsletter, TLDR Dev (paid). v1 focus on free channels first.

---

## 7. Launch sequence (2 weeks)

| Day | Action |
|-----|--------|
| D-3 | Record demo GIF; publish GitHub Release notes |
| D-2 | Dev.to article; enable Discussions |
| D-1 | Soft post in Playwright Discord / niche Slack |
| D0 | Show HN (morning PT) |
| D0+4h | r/playwright |
| D1 | r/selfhosted or r/QualityAssurance |
| D2 | LinkedIn + X thread |
| D3 | r/opensource |
| D4–7 | Reply all comments; merge doc/UX fixes from feedback |
| D7 | PR to one awesome-list |
| D14 | Retrospective post: “What we learned launching an OSS QA tool” |

---

## 8. Ongoing content (month 1–3)

Rotate **one piece per week**:

1. “How flow inference works” (technical)
2. “Selector healing: why human-in-the-loop” (opinion)
3. “Scaling workers with Celery” (ops)
4. “Visual regression without a SaaS tax” (comparison)
5. “Adding OIDC to an internal QA dashboard” (enterprise-adjacent)
6. Contributor spotlight / merged PR
7. Roadmap poll for v2 (billing, migrations, observability)

Each piece ends with: GitHub link + specific question (drives comments).

---

## 9. Community & contributors

Promotion sustains if people **send PRs**:

- Label issues: `good first issue`, `help wanted`, `discussion`
- Thank contributors in Release notes
- Monthly “office hours” GitHub Discussion thread
- Respond to Issues within 48h

**Contributor magnets (cheap wins):**
- “Add support for framework X login flow”
- “Document AWS ECS compose profile”
- “Improve heuristic for SPA nav without full page load”

---

## 10. Metrics (track weekly)

| Metric | Tool | Goal (8 weeks) |
|--------|------|----------------|
| GitHub stars | Insights / star-history | 100+ organic |
| Clone traffic | GitHub Traffic | Watch trend |
| Referrers | GitHub Traffic | Diverse (HN, reddit, dev.to) |
| Discussions / Issues | GitHub | Response time < 48h |
| Docker pulls | If published to GHCR later | Optional |
| Demo completions | Ask in Discussion poll | Qualitative |

Do **not** optimize only stars — optimize **issues from real users** and **PRs**.

---

## 11. What not to do

- Mass DM developers on LinkedIn/Twitter with repo link
- Post identical text to 10 subreddits same day
- Claim “production-ready SaaS” — README says otherwise
- Buy stars, upvotes, or PH votes
- Argue with HN security feedback — thank them and link hardening docs
- Hide that AI features need an API key

---

## 12. v2 teaser (future promotion hook)

When billing/Stripe lands, run a **second launch wave**:

- “Self-host free forever; paid cloud optional”
- Compare to SaaS QA tools on **price + data ownership**
- Target r/startups and indie hacker circles

Keep v1 narrative pure: **no paywall, MIT, experiment locally.**

---

## Quick links

- Repo: https://github.com/rishavsunny12/QABot
- Release: https://github.com/rishavsunny12/QABot/releases/tag/v1.0.0
- Demo: README “Demo Walkthrough” (TodoMVC, ~5 min)

---

*Last updated: v1.0.0 OSS launch.*
