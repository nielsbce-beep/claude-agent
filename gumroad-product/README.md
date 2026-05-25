# Life Agent — Your AI-powered Daily OS

> A Python system that pulls your real data — recovery, calendar, goals, portfolio —
> and runs it through 6 AI agents to plan your day. Every morning. Automatically.

---

## What it does

**Morning briefing** (runs at 07:00)
- Reads your Whoop recovery score, HRV and sleep data
- Shows today's calendar events
- Lists your active goals sorted by urgency
- Checks whether you kept yesterday's commitment
- Generates 3 concrete focus points for today using Claude

**Evening check-in** (runs at 21:00)
- Interactive 5-minute review of your day
- Logs wins, blockers and energy level
- Sets a commitment for tomorrow
- Updates goal progress automatically

**Weekly review** (runs Sunday at 10:00)
- Full analysis of the past week across all data sources
- AI-generated insights and concrete next steps per goal
- Saved to `data/weekly_reviews.json`

**Goals coach**
- Chat with an AI coach about your goals
- SMART goal creation, milestone tracking, accountability
- Daily and weekly check-in modes

**Journal**
- Free-form daily writing with AI follow-up questions
- Pattern detection across 14 days (mood trends, recurring blockers)
- Metadata extraction: mood, energy, wins, tags

**Board (6-agent debate)**
- Ask any question, get perspectives from 6 specialized agents:
  - 📅 Planning — time management, realistic scheduling
  - 💪 Sport — training, recovery, Whoop analysis
  - 💰 Money — financial advice, ROI, wealth building
  - 🚀 Opportunities — growth, skills, trends
  - 🎯 Critic — blind spots, uncomfortable truths
  - 🔥 Motivation — mindset, energy, accountability
- Agents see each other's responses and reach consensus

**Portfolio tracker**
- Overview of all holdings with returns
- Compound projections to your target amount
- Scenario analysis (bull/base/bear)
- AI analysis of your allocation

---

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) (~€0.01 per briefing)
- Optional: Whoop device + developer account
- Optional: iCloud calendar

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys. At minimum you need `ANTHROPIC_API_KEY`.
Everything else is optional — the system degrades gracefully without Whoop or iCloud.

### 3. Set up your goals

Copy `data/goals_example.json` to `data/goals.json` and edit it with your own goals,
or use the goals coach to create them interactively:

```bash
python goals_coach.py chat
```

### 4. Set up your portfolio (optional)

Copy `data/portfolio_example.json` to `data/portfolio.json` and fill in your holdings.

### 5. Connect Whoop (optional)

```bash
python cli.py whoop_login
```

This opens a browser for OAuth. Token is saved locally and refreshes automatically.

### 6. Run your first briefing

```bash
python morning_briefing.py
```

---

## Running automatically

To run the full daily schedule (briefing at 07:00, check-in at 21:00, weekly review Sundays):

```bash
python scheduler.py
```

Run once in the background at startup (e.g. add to your `.bashrc` or Windows Task Scheduler).

---

## Usage — all commands

### Daily flows

```bash
python morning_briefing.py       # Morning briefing
python avond_checkin.py          # Evening check-in
python weekly_review.py          # Weekly review (any time)
```

### Goals

```bash
python goals_coach.py chat       # Open chat with your goals coach
python goals_coach.py check-in   # Quick daily check-in on all goals
python goals_coach.py review     # Weekly review of all goals
python goals_coach.py lijst      # List all active goals
```

### Journal

```bash
python journal_agent.py schrijven    # Write a journal entry
python journal_agent.py patronen     # Analyse patterns (last 14 days)
python journal_agent.py log          # Show recent entries
```

### Board (multi-agent debate)

```bash
python board.py "Should I skip the gym today?"
python board.py "Is it smart to invest in X right now?"
python board.py sport "My knee hurts, what should I do?"
python board.py geld "Should I increase my monthly contribution?"
```

### Portfolio

```bash
python financieel_agent.py overzicht     # Portfolio overview
python financieel_agent.py projectie     # Compound projections
python financieel_agent.py analyse       # AI analysis
python financieel_agent.py update        # Update holdings manually
```

### CLI shortcuts

```bash
python cli.py status             # Whoop recovery + today/tomorrow agenda
python cli.py dagplan            # Generate day plan based on recovery
python cli.py weekplan           # Plan 7-day training schedule
python cli.py agendas            # List available iCloud calendars
```

---

## Without Whoop

The system works fine without a Whoop. Recovery sections will show "No data available"
and the AI agents will skip recovery-based advice. Everything else works normally.

If you have Whoop CSV exports (from the Whoop app), place them in `data/`:
- `physiological_cycles.csv`
- `sleeps.csv`
- `workouts.csv`

The system will use these as a fallback for trend analysis.

---

## Without iCloud

Set `ICLOUD_USERNAME` and `ICLOUD_APP_PASSWORD` to empty strings in `.env`.
The calendar section will show "No events found." The rest works fine.

The system uses the calendar named `"My AI Agenda"` by default (set via `CALENDAR_NAME` in `.env`).
Change this in `morning_briefing.py` and other files — search for `calendar_name=`.

---

## Customizing the AI tone

Every agent has a system prompt you can edit directly.

- Morning briefing focus coach: `morning_briefing.py` → `_section_focus()` → `system=`
- Evening coach: `avond_checkin.py` → system prompts in `_ask_*` functions
- Board agents: `agents/critic_agent.py`, `agents/motivation_agent.py`, etc.

The default tone is direct and Dutch. Change the language in the system prompts to switch to English.

---

## File structure

```
life-agent/
├── morning_briefing.py     # Daily morning output
├── avond_checkin.py        # Daily evening check-in
├── weekly_review.py        # Weekly review
├── goals_coach.py          # Goals chat interface
├── financieel_agent.py     # Portfolio tracker
├── journal_agent.py        # Journal + pattern analysis
├── board.py                # Multi-agent debate
├── cli.py                  # CLI shortcuts
├── scheduler.py            # Automatic daily schedule
├── critic_coach.py         # Standalone critic agent
├── agents/
│   ├── base_agent.py       # Base class for all board agents
│   ├── planning_agent.py   # Day/week planning utilities
│   ├── planning_board_agent.py
│   ├── sport_agent.py
│   ├── money_agent.py
│   ├── critic_agent.py
│   ├── motivation_agent.py
│   └── opportunity_agent.py
├── tools/
│   ├── goals_store.py      # Goals persistence (JSON)
│   ├── calendar_tools.py   # iCloud Calendar (caldav)
│   ├── whoop_api.py        # Whoop OAuth2 + REST
│   └── whoop_history.py    # Whoop CSV analysis
└── data/
    ├── goals.json           # Your goals (create from example)
    ├── portfolio.json       # Your portfolio (create from example)
    ├── growth_log.json      # Daily commitments log
    ├── journal.json         # Journal entries
    └── weekly_reviews.json  # Weekly review history
```

---

## Cost

The system calls the Claude API. Typical usage:

| Action | Tokens | Cost (approx.) |
|--------|--------|----------------|
| Morning briefing | ~800 | €0.004 |
| Evening check-in | ~600 | €0.003 |
| Board (all 6 agents) | ~3000 | €0.015 |
| Weekly review | ~1500 | €0.008 |

**~€0.10–0.20 per month** at daily use. Cheaper than any SaaS.

---

## Questions / issues

Built by a TU Delft student. If something doesn't work, open an issue or reach out directly.

The system is actively used daily — bugs get fixed fast.
