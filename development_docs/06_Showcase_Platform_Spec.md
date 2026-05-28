# SecureClaim AI — Resilience Console (Showcase Platform Spec)

**Version:** 1.0
**Date:** May 27, 2026
**Status:** Final v2.0
**Author:** Athish G R
**Classification:** Internal

---

## 1. Purpose

The **Resilience Console** is the public-facing showcase artifact. Its single job is to convince a technical reviewer, in 10–20 minutes of unattended exploration, that the builder genuinely understands how to design and ship a resilient multi-agent AI system.

It is **not** an insurance product website. It is a security engineering portfolio piece with the insurance pipeline as a live, attackable specimen behind it.

### Design north star
> "Looks like a security operations console for a serious system. Reads like documentation. Behaves like a product."

### What the Console must achieve

| Outcome | How it manifests |
|---------|------------------|
| Convince in 30 seconds | Hero shows live attack counter, last blocked attempt with timestamp, "successful breaches" counter (0 if true). No marketing prose. |
| Convince in 5 minutes | Reviewer launches the **Attack Playground**, fires three attack templates, sees the layer-by-layer defense trace render in real time, clicks through to audit-log evidence and to the GitHub line that implements the defense. |
| Convince in 20 minutes | Reviewer reads the **Defense Pattern Library** (named patterns with citations), explores the **Architecture Explorer** (clickable interactive diagram), filters the **Attack-Defense Matrix** by category, watches the **Adversarial Agent live feed**, and replays a recent session step-by-step. |
| Earn trust on inspection | **Residual Risk Register**, **Formal Spec page**, **Audit Chain Integrity** badge, **Cost & Token Dashboard**, **API Explorer**, **GitHub deep-links from every claim**. Honesty everywhere; no unsupported numbers. |

---

## 2. Audiences (in priority order)

| Priority | Audience | What they want | Time budget |
|----------|----------|----------------|-------------|
| P0 | Hiring manager / principal engineer | "Is this person credible?" | 5–15 min unsupervised |
| P0 | AI security researcher | "Can I actually try to break this?" | 15+ min, possibly returns |
| P1 | Curious developer | "How is this built?" | 5 min |
| P2 | Recruiter (non-technical) | "What's the headline?" | 30s before forwarding to a technical reviewer |
| P3 | Future maintainer (the builder six months later) | "Where is X?" | as needed |

---

## 3. Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Density over decoration** | Information-rich layouts. No hero illustrations. Whitespace is functional, not aesthetic. |
| **Numbers, not adjectives** | Never "highly secure"; always "blocked 153/153 variants over 12 minutes." Every claim links to evidence. |
| **Show the work** | Every defense links to the code (GitHub line-anchored), the test (file + run), and the pattern (Library page). |
| **Telemetry as first-class content** | OTel traces, audit rows, security events render inline with prose. The reader sees real data, not stock screenshots. |
| **Inspectable, not just viewable** | Every visible value is keyboard-selectable; structured data is exportable as JSON; URLs encode state for sharing. |
| **No marketing emoji, no stock photo, no "Made with love"** | Footer: "Engineered by Athish G R. MIT-licensed. PRs welcome." That's it. |
| **Earn trust by admitting limits** | The Residual Risk Register is one click from anywhere. Limitations are linked, not buried. |
| **Speed signals quality** | LCP < 1.5s, TTFB < 200ms. Demonstrates the builder cares about craft. |
| **Accessibility is a credibility signal** | WCAG 2.1 AA. Keyboard navigation everywhere. Screen-reader pass. |

---

## 4. Visual Design System

### 4.1 Aesthetic
Dark, monospaced, terminal-inspired. The system should evoke a SOC dashboard / security tool, not a SaaS marketing site.

### 4.2 Colour System

```
Background scale (dark, default theme)
  bg-0   #0A0E14   page background
  bg-1   #0F141B   panel background
  bg-2   #161C24   raised panel
  bg-3   #1E2632   borders, dividers

Foreground scale
  fg-0   #E6EDF3   primary text
  fg-1   #B0BAC6   secondary text
  fg-2   #6E7B8C   tertiary text (timestamps, captions)
  fg-3   #3D4856   disabled / very low emphasis

Signal palette (semantic)
  ok        #4ADE80    defenses firing successfully, healthy state
  warn      #F5B056    detection without block, partial leak
  alert     #F25B5B    successful breach, broken invariant
  attack    #C879FF    attack-related accents (sparingly)
  trust     #5BB5F2    trust labels (PUBLIC/PERSONAL/CONFIDENTIAL/SECRET)
  audit     #8B96A8    audit chrome

Trust label colours (used consistently across UI)
  PUBLIC        #4ADE80
  PERSONAL      #F5B056
  CONFIDENTIAL  #F25B5B
  SECRET        #C879FF
  UNTRUSTED     #6E7B8C  with diagonal hatching pattern
```

Light theme exists but ships as opt-in; dark is default. No theme-flip animation; it's just a setting.

### 4.3 Typography

| Use | Family | Notes |
|-----|--------|-------|
| Headings (sparingly used) | Inter | semi-bold, tight tracking |
| Body | Inter | 15px/24 line height; comfortable reading |
| Code, logs, JSON, traces, attack payloads, identifiers, timestamps | JetBrains Mono | 13–14px; this is the working font of the site |
| Numbers (large display) | JetBrains Mono | tabular figures |

Code-mono carries roughly 50–60% of the visible text. This is a *security tool*, not a brochure.

### 4.4 Motion

| Pattern | Use |
|---------|-----|
| Layer-by-layer reveal | Defense trace: each layer pane fades-in 50–80ms after the previous; subtle |
| Pulse | "Live" indicators (one slow pulse per 2s) |
| Slide-in | New audit rows appearing in live stream (200ms cubic-bezier) |
| Cursor blink | Terminal-style cursor in the playground input |
| No bouncy springs, no parallax, no scroll-triggered animations | Motion is functional |

### 4.5 Components

The component library is built on **shadcn/ui** with custom primitives:

- `Panel` — bordered raised surface with optional toolbar
- `KeyValueGrid` — left-label, right-value table; the working layout for spec data
- `LogRow` — single-line entry with timestamp, severity glyph, monospace content
- `LabelBadge` — coloured pill for trust labels
- `AttackBadge` — pill showing attack ID + category
- `PatternBadge` — pill showing pattern ID (P1–P12) + name
- `CodeBlock` — Shiki-highlighted with copy + GitHub deep-link icons
- `TraceTimeline` — vertical timeline of spans
- `JsonInspector` — collapsible JSON tree
- `DiffView` — for showing prompt-registry diffs, RAG corpus diffs
- `LiveCounter` — large monospace counter with subtle pulse on update
- `StatusDot` — green/yellow/red live indicator
- `Sparkline` — 60-data-point inline chart
- `Heatmap` — for attack × defense-layer matrix views
- `EvidenceLink` — pill that links to audit row + GitHub + test file
- `BreachAlert` — full-width prominent banner for successful-breach state

---

## 5. Information Architecture

### 5.1 Top-level navigation (persistent header)

```
SECURECLAIM AI — Resilience Console
─────────────────────────────────────────────
  Playground  ·  Architecture  ·  Matrix  ·  Patterns
  Adversary   ·  Audit Feed     ·  Demo   ·  Docs
                                       [⌘K]  [GitHub]
```

Header always shows:
- **System status dot** (green / yellow / red)
- **Live counters:** "Attacks today: NN · Blocked: NN · Successful: 0"
- **Build SHA** (clickable → GitHub commit)
- **Command palette** trigger (⌘K)

### 5.2 Pages

| Path | Page | Purpose |
|------|------|---------|
| `/` | Home | 30-second pitch with live signals |
| `/playground` | Attack Playground | The flagship interactive feature |
| `/architecture` | Architecture Explorer | Interactive system diagram |
| `/matrix` | Attack-Defense Matrix | The full 79-row table with numbers |
| `/matrix/:attackId` | Attack detail | Drill-down per attack |
| `/patterns` | Defense Pattern Library | P1–P12 with citations |
| `/patterns/:patternId` | Pattern detail | One pattern, full treatment |
| `/adversary` | Adversarial Agent Dashboard | Live feed + stats |
| `/audit` | Live Audit Feed | Real-time event stream |
| `/audit/:traceId` | Session replay | Step-through of one session |
| `/demo` | Claim Demo | The happy-path pipeline |
| `/formal` | Formal Specification | TLA+ spec rendered + conformance status |
| `/residual` | Residual Risk Register | Honest limitations |
| `/api` | API Explorer | Swagger-style live API docs |
| `/docs` | Documentation Hub | All six docs, web-rendered |
| `/about` | About / Builder | Brief; links to LinkedIn, GitHub |

---

## 6. Page Specifications

### 6.1 Home (`/`)

**Above the fold:**
- Header (see §5.1).
- Single H1: `Resilient agentic AI, demonstrated.`
- Sub-line, monospace: `// A multi-agent claims platform engineered against a 79-category attack taxonomy.`
- **Live signal panel** (three columns, no decoration):
  ```
  Hours since last successful breach   |  Attacks tried today  |  Defenses currently armed
  ─────────────────────────────────────┼──────────────────────┼──────────────────────────
  741h 12m                              |  1,247                |  12 patterns / 79 attacks
  ```
- **Three primary CTAs** (each a card with one verb):
  - `Try to break it →` (→ /playground)
  - `Inspect the architecture →` (→ /architecture)
  - `See the matrix →` (→ /matrix)

**Below the fold:**
- **"What this is"** — one paragraph, four lines max. Cites the taxonomy file.
- **Last 10 attacks ticker** — live SSE; each row clickable to its session replay.
- **Five named patterns** — small cards with one-line summaries (rotating selection from P1–P12).
- **Footer:** Engineered by · GitHub · MIT · build SHA · last-CI-run badge.

**What must NOT appear:** stock photography, "trusted by" logos, testimonials, animated background, marketing copy about "unlocking value." None of those things.

### 6.2 Attack Playground (`/playground`)

**The flagship page.** Reviewer experience must be: open page → fire an attack within 15 seconds → see defense response visualised within 2 seconds.

**Layout: full-width split pane.**

#### 6.2.1 Left pane — Attack composer

Tabbed:
- **Chat injection** — text area; pre-loaded template picker ("Try one of:" → 20 starting payloads from taxonomy categories #1, #4, #7, #21, #25, #28, #29, #65, #66, #78).
- **Upload PDF** — drop zone; pre-loaded sample adversarial PDFs (white-on-white injection; embedded JS; hidden-form payload).
- **Upload image** — drop zone; pre-loaded samples (overlay text; sticker; watermark; multi-overlay).
- **Tool-misuse simulation** — pick an agent, pick a tool the agent shouldn't have, set parameters; observe capability-token denial.
- **Cross-customer probe** — pick "customer A" session, try to query "customer B" data; observe RLS denial.
- **Custom attack** — free-form payload + structured "intended attack ID" selector.

Each composer has a "Run as authenticated session" toggle and a "Run as fresh session" toggle. A separate **"Target flow"** selector lets the reviewer aim the attack at either the **claim-filing path** or the **customer-inquiry path** (see TAD §3.3); many attack categories (#21, #27, #65, #66, #78) have surface-specific templates for each, so the reviewer can compare how the same defense responds to differently-shaped attacks against differently-shaped flows.

#### 6.2.2 Right pane — Defense Trace

Renders as the attack flows through the system. Each layer is one collapsible panel; panels appear sequentially with a subtle slide-in.

```
DEFENSE TRACE  ·  trace_id: 8f3c…1a    [share] [export JSON] [replay]

▾ LAYER 1: Ingress Sanitisation        20ms       NORMALISED
   ✓ Unicode NFKC applied
   ✓ Stripped 3 zero-width chars
   • Encoding modifications visible (toggle to view diff)

▾ LAYER 2: Pattern Detection           4ms        2 hits
   • "ignore previous" matched (severity: info)
   • "system:" matched (severity: info)

▾ LAYER 3: Semantic Classifier         180ms      score: 0.91
   • Above threshold (0.7) → security_event written

▾ LAYER 4: Untrusted Tagging           1ms        TAGGED
   • Wrapped in <untrusted> delimiters; label = UNTRUSTED

▾ LAYER 5: Parser LLM (quarantined)    640ms      SCHEMA_OK
   • Output: { "intent": "policy_query", "fields": {...} }
   • No tool access. Output forwarded structured.

▾ LAYER 6: Actor LLM (privileged)      820ms      RESPONSE
   • Operating on structured input; never saw raw text.
   • Tool call: search_public_faq("how do i file...")  ✓ allowed

▾ LAYER 7: Egress Filter               12ms       CLEAN
   • PII scan: 0 hits
   • URL allowlist: 1 URL (allowed: docs.secureclaim.example)
   • Label-aware redaction: no SECRET sources

═══════════════════════════════════════════════════════════
VERDICT
   Attack vector matched: #1 Direct Prompt Injection
   Outcome:  BLOCKED · structural (P1 dual-LLM)
   Surfaced data: none
   Audit rows written: 11
   Security events: 1 (pattern_detect_hit), 1 (semantic_score_high)

[Evidence: open audit rows] [Defense code: github/parser.py:L62]
[Pattern: P1 — Dual-LLM Separation]
```

Every panel is keyboard-navigable. Every reference is a real link. Every JSON is a real `JsonInspector`. The trace is a *real OpenTelemetry trace*, not a mockup.

#### 6.2.3 Below trace

- "Compare with naïve baseline" toggle: re-runs the same payload against a stub baseline (no P1, no P10) so the reviewer sees what would happen without the architecture. **This is the single most persuasive thing the page can do.**

#### 6.2.4 Empty state

When the reviewer hasn't yet submitted anything, the right pane shows:
- A short paragraph explaining what they're about to see.
- A diagram preview of the layers.
- The most recent five trace summaries from other users (anonymised).

### 6.3 Architecture Explorer (`/architecture`)

Interactive system diagram (React Flow). The diagram from Doc 02 §1.3, but live.

- **Nodes:** sanitisation layers, parser LLMs, orchestrator, actors, tool registry, data stores, egress filter, observability.
- **Edges:** message flows; colour-coded by trust label of the data flowing.
- **Click node:** side-panel slides in with that node's spec (role, model, tools, label access, code reference, recent traffic histogram).
- **Click edge:** message-schema viewer, with sample real message from recent traffic.
- **Trace mode:** select a `trace_id` (or one from a list of recent traces); the diagram highlights the path with arrows, durations, and inline tooltips.
- **Filter:** "show only defenses against #N" → highlights only the nodes/edges that participate in defending attack #N.

Power features:
- Zoom + minimap.
- Search (cmd+K) for any node/edge name.
- Export current view as SVG.

### 6.4 Attack-Defense Matrix (`/matrix`)

The full 79-row table. Filters + drill-down.

**Filters (chips at top):**
- Class: `LIVE · ARCHITECTURAL · OUT-OF-SCOPE`
- Category: `Prompt/Input · Goal Hijack · Memory · Exfiltration · Tool · Identity · Multi-Agent · Supply Chain · Training · Cascading · Trust · Infra · Weapon · Privacy`
- Pattern: `P1 … P12`
- Status: `ok · warn · alert`

**Default sort:** by class (LIVE first), then by attack ID.

**Columns:**

| # | Name | Class | Patterns | Variants | Blocked | Partial | False+ | Last run | Status |
|---|------|-------|----------|----------|---------|---------|--------|----------|--------|
| 1 | Direct Prompt Injection | LIVE | P1,P10 | 153 | 153 | 0 | 2 | 14m ago | ok |
| 2 | Indirect (PDF) | LIVE | P1,P5,P3 | 92 | 91 | 1 | 0 | 2h ago | warn |
| 6 | Multimodal | LIVE | P6,P5,P1 | 47 | 47 | 0 | 1 | 3h ago | ok |
| 43 | Orch Privilege Escalation | ARCHITECTURAL | P2 | — | — | — | — | — | ok |
| 56 | Data Poisoning | OUT-OF-SCOPE | — | — | — | — | — | — | n/a |

**Heatmap toggle:** switches the table to a heatmap of attack categories × defense layers, intensity = number of variants handled. Visual at-a-glance.

**Drill-down (`/matrix/:attackId`):**
- Attack description (verbatim from taxonomy)
- Class + rationale
- Patterns + links to pattern detail pages
- Defense summary (from Doc 04)
- Code references (GitHub line-anchored)
- Test file (GitHub line-anchored)
- Run history table (last 20 runs with numbers)
- Sample evidence: 3 recent traces (each → playground replay)
- For ARCHITECTURAL: assertion test file + citation
- For OUT-OF-SCOPE: rationale + framework reference

### 6.5 Defense Pattern Library (`/patterns`)

P1–P12. One card per pattern on the index page.

**Each card:**
- Pattern ID + name
- One-sentence summary
- "Defends attacks #X, #Y, #Z" (clickable to matrix-filtered view)
- Tiny animated diagram (Framer Motion) showing the pattern in action

**Detail page (`/patterns/:id`):**
- **Problem** — what attack class this defeats and why naïve approaches don't
- **Pattern** — the architectural shape, with an interactive diagram
- **Implementation** — code blocks (Shiki, copy-able) with GitHub deep-links
- **Defends** — list of attack IDs with click-throughs
- **References** — academic and practitioner sources:
  - P1 → Simon Willison's "Prompt Injection Explained", Anthropic Constitutional Classifiers paper
  - P3 → Myers & Liskov "Complete, Safe Information Flow" (POPL '97)
  - P4 → Capabilities literature (Dennis & Van Horn '66), Object-capability model
  - P7 → PostgreSQL RLS docs
  - P9 → Merkle trees, certificate transparency
  - … etc.
- **Residual risk** — honest discussion of what the pattern doesn't cover
- **Compare** — "without this pattern, attack #X looks like:" (links to baseline replay)

This page is the **substance proof** that the builder isn't just shipping a regex layer. The citation density is the point.

### 6.6 Adversarial Agent Dashboard (`/adversary`)

The autonomous attacker's home page.

**Top strip:**
- Hours running continuously
- Attempts tried (cumulative + last 24h)
- Successful breaches (very large counter; red if non-zero, green if zero)
- Cost this month (vs cap)

**Middle:**
- **Live feed** (SSE): scrolling list of attempts with attack-ID badge, target endpoint, outcome, defense layer that blocked.
- Click an attempt → opens its playground replay.

**Charts:**
- Attempts/hour over last 7 days (sparkline + histogram)
- Attack-category distribution (pie / bar)
- Block-layer distribution (which patterns are most active)
- Cost over time

**Strategy panel:**
- The adversarial agent's current strategy (its system prompt, displayed verbatim)
- Strategy diff over time (when prompt evolves, shown as a diff)

**Breach panel** (visible only when breaches > 0):
- BIG red banner
- Per-breach: attack ID, timestamp, payload, what leaked, GitHub issue link, current fix status

Honesty is the point. If there are breaches, show them. The builder's competence is more strongly demonstrated by *handling* breaches transparently than by claiming none.

### 6.7 Live Audit Feed (`/audit`)

Real-time scrolling feed of audit rows, SOC-dashboard style.

**Toolbar:**
- Filters: agent · action · severity · label · trace_id
- Time range
- Pause / resume
- Export filtered → JSON / CSV

**Row format:** monospace, single line where possible:
```
12:04:18.221  trace=8f3c…1a   agent=claims_processor   tool_call=score_fraud      label=SECRET     ok
12:04:18.604  trace=8f3c…1a   agent=settlement_actor   capability_use=request_payout  scope=CLM-123  denied(scope_mismatch)
12:04:18.612  trace=8f3c…1a   event=capability_denied  attack_id=29              severity=warn
```

Click a row → expand inline (JSON inspector). Click `trace=…` → session replay page.

**Audit chain integrity badge** in toolbar: last-verified timestamp + chain-root hash. Click → run verification on demand.

### 6.8 Session Replay (`/audit/:traceId`)

Time-travel debugger for a single session.

- Vertical timeline of all audit rows + spans
- Scrub bar at top; drag to step through time
- Diagram pane: highlights nodes/edges as the scrub moves
- State panel: shows claim state at scrub position (DB values reconstructed from audit details)
- Decisions panel: shows each tool call, parser output, actor response at scrub position
- Share button: URL encodes `?at=12.4s`
- "Diff against baseline" toggle: if this trace was a playground attack, side-by-side with the naïve baseline replay

This is the page that turns "we have audit logging" into something a reviewer can *use*.

### 6.9 Claim & Inquiry Demo (`/demo`)

The intended happy-path UX for both supported flows, for context. The page exists so reviewers see the system *works*, not just that it defends.

- Chat interface (simulates John, the policyholder)
- Upload widget
- Live state ribbon showing claim stage *or* inquiry intent
- On settlement (or inquiry resolution), shows the audit + traces below as a collapsed receipt
- **Two flow categories** of scripted scenarios, each loadable with one click:
  - **Claim filing**: Minor / Major / Total-loss / Fraud-flagged / Identity-fail
  - **Customer inquiry**: FAQ (pre-identity) / Claim-status-lookup / Policy-question / Complaint-capture / Identity-fail-on-inquiry
- Each scenario runs through the real system live; the reviewer can interrupt and chat freely at any point

### 6.10 Formal Specification (`/formal`)

- Rendered TLA+ spec (syntax-highlighted)
- State diagram of reachable states (auto-generated from TLC output)
- Invariants listed with TLC verification status (last-checked timestamp)
- Conformance-test status badge
- Link to GitHub `formal/workflow.tla`
- One-paragraph plain-English explanation of what the spec actually proves and what it doesn't

### 6.11 Residual Risk Register (`/residual`)

Honest list of what the system does *not* cover and why. Linked from every page footer.

Each entry:
- Risk description
- Why it remains (cost, scope, time, fundamental limitation)
- What would mitigate it in a real production deployment
- Status: `accepted · planned · won't-do`

### 6.12 API Explorer (`/api`)

Swagger-style live docs of the `/showcase` API. Includes:
- Try-it-out buttons (rate-limited)
- Schemas
- Auth notes ("most endpoints are public; playground submission is rate-limited per IP")
- Curl examples

This page is for the engineer who wants to see "is there a real API behind this, or just a frontend?"

### 6.13 Documentation Hub (`/docs`)

All six markdown docs rendered as styled web pages with:
- Table of contents
- Inline links between docs
- Code blocks deep-linking to GitHub
- "Last updated" + commit link
- Print-friendly view

### 6.14 About (`/about`)

One short page:
- Builder's name, photo, one-paragraph bio
- "Why this project" — three sentences
- Tech stack badges (Anthropic Claude, Postgres, OpenTelemetry, TLA+, Next.js, etc.)
- Links: GitHub repo, LinkedIn, email

No "personal brand" copy. No "passionate about." Just the facts.

---

## 7. Interaction Patterns

### 7.1 Command Palette (⌘K / Ctrl+K)

Available on every page. Powered by `cmdk`.

Commands:
- **Navigate** to any page (typed name)
- **Find attack** by ID or keyword
- **Find pattern** by ID or keyword
- **Open trace** by trace_id
- **Open recent playground attempts**
- **Run an attack template**
- **Toggle dark/light**
- **Open GitHub repo**
- **Copy current page URL**

Power-user signal: keyboard navigation is fast and complete.

### 7.2 URL state encoding

Every interaction encodes state in the URL:
- `/playground?template=indirect-pdf-3` loads the playground with a specific template ready
- `/audit?agent=settlement_actor&severity=warn` deep-links to filtered feed
- `/audit/8f3c1a?at=12.4s` deep-links to a scrubbed-in replay
- `/matrix?class=LIVE&pattern=P1` filtered matrix

Reviewers can share specific findings. The builder can demo specific scenarios with a single URL.

### 7.3 Sharing & embeds

- Every page has a `Share` button → copies URL with current state
- Playground sessions get permanent replay URLs
- `?embed=1` strips header/footer/nav for iframe embedding (useful for the GitHub README or a LinkedIn post)
- OG images dynamically generated for shared playground URLs ("Attack #29 · Blocked at Layer 5 — see the trace")

### 7.4 Notifications

Subtle toast for:
- "New attack tried (open trace)"
- "Adversarial agent succeeded — view breach"
- "CI run failed — see test report"

Toasts auto-dismiss; click to expand to full event.

### 7.5 Comparison mode

On playground and matrix detail pages, a "Compare" toggle runs the same payload against a baseline configuration (no P1, no P10) and shows side-by-side traces. **This is the single most persuasive interaction on the site** — the reviewer sees the architecture's contribution made concrete.

---

## 8. Live Data Architecture

### 8.1 Data flow

```
Agent system (API) ──── REST ────→  Console (SSR / RSC)
                  ──── SSE  ────→  Live streams (audit, adversarial)
                  ──── WS   ────→  Playground bidirectional

CI runs ──── webhook ──→ matrix-data updater
Adversarial agent ──── stdout ──→ adversarial-stream
OTel traces ──── Tempo ──→ replay viewer
```

### 8.2 SSE channels

| Channel | Payload | Cadence |
|---------|---------|---------|
| `/sse/audit` | new audit rows | per event, ≤200/s |
| `/sse/adversarial` | adversarial attempts | per attempt, ≤1/s |
| `/sse/health` | system status + counters | every 5s |
| `/sse/playground/:traceId` | defense-trace events | per layer, ≤10 events per attack |

### 8.3 Caching

- Static pages (Pattern Library, Architecture description, About): RSC + ISR (revalidate hourly)
- Matrix data: revalidate on CI webhook
- Live streams: no caching
- Replays: cacheable per trace_id

### 8.4 Failure modes

- API unreachable → red status dot + amber banner; pages render last-known cached data with timestamp
- Adversarial agent paused → indicated on dashboard; reason linked
- Cost cap hit → adversarial dashboard shows "throttled by budget" with timestamp

---

## 9. Performance & Accessibility

### 9.1 Performance targets

| Metric | Target |
|--------|--------|
| LCP | <1.5s |
| TTFB | <200ms |
| CLS | <0.05 |
| INP | <200ms |
| JS shipped (initial) | <120kB |
| Playground attack → first layer rendered | <500ms |
| Playground attack → verdict | <2s p95 |

Measured via Vercel Analytics; surfaced as a badge on the About page ("This site's own performance is part of the credibility signal").

### 9.2 Accessibility

- WCAG 2.1 AA
- Full keyboard navigation; focus rings visible (custom, not default)
- Screen-reader pass on all interactive components
- Colour contrast ≥4.5:1 for body, ≥3:1 for large text
- `prefers-reduced-motion` respected (motion replaced with instant transitions)
- All charts have data-table equivalents toggleable

### 9.3 Cross-platform

- Desktop: primary target
- Tablet: full functionality
- Mobile: read-only for matrix, patterns, audit; playground shows a "best viewed on desktop" note but still works for chat injection

---

## 10. Technology Stack (Console)

| Layer | Technology |
|-------|------------|
| Framework | Next.js 15 (App Router, RSC) |
| Styling | Tailwind 3 + shadcn/ui + custom design tokens |
| State | TanStack Query v5 |
| Live data | EventSource (SSE) + native WebSocket |
| Diagrams | React Flow |
| Charts | Visx |
| Code rendering | Shiki |
| Command palette | cmdk |
| Motion | Framer Motion (used sparingly) |
| Forms | react-hook-form + zod |
| Icons | Lucide |
| Testing | Vitest + Playwright |
| Hosting | Vercel (Edge) |
| Analytics | Vercel Analytics |
| Error monitoring | Sentry (free tier) |

---

## 11. Build & Deployment

### 11.1 Repository layout

```
console/
├── app/                          # Next.js App Router
│   ├── (marketing)/page.tsx      # Home
│   ├── playground/
│   ├── architecture/
│   ├── matrix/[attackId]/
│   ├── patterns/[id]/
│   ├── adversary/
│   ├── audit/[[...path]]/
│   ├── demo/
│   ├── formal/
│   ├── residual/
│   ├── api/
│   └── docs/[...slug]/
├── components/
│   ├── primitives/               # design system
│   ├── playground/
│   ├── architecture/
│   ├── matrix/
│   └── live/                     # SSE consumers
├── lib/
│   ├── api.ts                    # API client
│   ├── sse.ts                    # SSE hooks
│   ├── ws.ts                     # WebSocket helpers
│   └── trust.ts                  # label rendering
├── public/
└── tests/
    ├── unit/
    └── e2e/                      # Playwright
```

### 11.2 CI

| Trigger | Action |
|---------|--------|
| PR | lint, unit, build, Playwright smoke |
| main merge | full Playwright suite, deploy to Vercel production |
| Backend CI green | webhook → revalidate matrix-data |
| Adversarial agent breach | webhook → notification + revalidate adversary page |

### 11.3 Environments

| Env | Purpose | URL |
|-----|---------|-----|
| Production | Public showcase | secureclaim.example |
| Preview | Per-PR previews | Vercel auto |
| Local | Dev | localhost:3000 |

Backend has matching `prod` and `sandbox` instances; the adversarial agent attacks the `sandbox` instance only.

---

## 12. Launch Checklist

- [ ] All pages render without console errors
- [ ] Playground works end-to-end with 5 attack templates
- [ ] Compare-with-baseline toggle works on playground
- [ ] Matrix has live numbers for ≥40 LIVE attacks
- [ ] Each P1–P12 pattern detail page has citations + code refs + animated diagram
- [ ] Replay URLs work for ≥10 recent traces
- [ ] Adversarial agent has run continuously for ≥72h pre-launch
- [ ] Audit chain integrity verifies clean
- [ ] Formal spec page renders TLA+ + conformance status
- [ ] Residual risk register has ≥10 honest entries
- [ ] Command palette covers all primary actions
- [ ] Lighthouse: Performance ≥95, Accessibility ≥100, Best Practices ≥100, SEO ≥95
- [ ] axe-core: zero violations on all pages
- [ ] Sentry: zero unresolved errors
- [ ] OG images render for share URLs
- [ ] README links to live Console with one-paragraph "what to try first"
- [ ] 5-min demo video uploaded and embedded on Home

---

## 13. Anti-Patterns to Refuse

These would lower the artifact below "professional security tool":

- ❌ Hero illustration or 3D rendering
- ❌ Marketing copy ("supercharge your AI", "next-generation", "enterprise-grade")
- ❌ Stock photography
- ❌ Testimonials / "trusted by" logos
- ❌ Pricing page, "contact sales", lead-gen forms
- ❌ Newsletter signup
- ❌ "Awards" badges, "as featured in"
- ❌ Animated background gradients
- ❌ Cookie banner beyond strict-minimum (analytics opt-in, not the banner-of-shame)
- ❌ Emoji in body content (sparing use in playground attack templates is fine since attacks themselves use them)
- ❌ "Watch the launch video!" full-page interstitial
- ❌ Auto-playing video anywhere

The Console signals seriousness through restraint.

---

## 14. Success Metrics (post-launch)

| Metric | How measured | Target |
|--------|--------------|--------|
| Reviewer playground engagement | % of visitors who fire ≥1 attack template | ≥40% |
| Matrix drill-down rate | % who click into ≥1 attack detail | ≥30% |
| Replay shares | distinct replay URL shares | meaningful organic share count |
| GitHub stars from Console traffic | UTM-tagged repo visits → stars | qualitative |
| Adversarial-agent breach disclosure | breaches handled transparently (issue → fix → audit) | 100% if any |
| Lighthouse score on Home | monthly | ≥95 Performance, 100 Accessibility |
| Reviewer feedback (qualitative) | direct outreach + LinkedIn responses | "this is impressive" or stronger |

---

*End of Resilience Console Specification — Document 6 of 6*
