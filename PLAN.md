# Sliced Bread — personal budget tracker (plan)

Python + Gradio. Runs the same way on a laptop and in Google Colab. Status: **draft, awaiting approval.**

## 1. What we're building

One question answered on one page: **how much do I have left to invest this month?**

The page reads top to bottom, the way money flows:

1. **Income** — every source (salary, freelance, other)
2. **Necessities** — rent, groceries, gas, utilities
3. **Discretionary** — movies, events, games, subscriptions
4. **Travel** — trip costs
5. **Investments** — whatever is left: `income − (necessities + discretionary + travel)`

No default line items. Each section starts empty with one line of guidance and a **+** button.

Maps to the brief's feature list:

| Brief asks for | Where it lives |
|---|---|
| Income tracking | Income section, total at the top |
| Expense tracking (amount, category, description) | Sections 2–4; the section *is* the category, the line name is the description |
| Overall + per-category budgets | Account page: one limit per section, plus an overall monthly limit |
| Automatic calculations | `budget.py`; every add or delete recomputes |
| Budget alerts | A meter under each section: near limit at 90%, over at 100% |
| Monthly summary | The hero line and stacked bar at the top of the page; month picker |
| Savings goal | Investments section: progress toward the goal set on the account page |

## 2. Screens

Two screens after sign-in, as tabs: **Budget** (landing) and **Account**. Before sign-in, only the sign-in card.

### Sign in

```
┌──────────────────────────────┐
│ Sliced Bread                 │
│ Know what's left each month  │
│                              │
│ Username [            ]      │
│ Password [            ]      │
│ [ Sign in ]  Create account  │
└──────────────────────────────┘
```

### Budget (landing) — one centered column, 640 px max

```
┌──────────────────────────────────────────────┐
│ $640 left to invest in October      Oct 2026▾│  ← hero: title states the answer
│ ███████████▓▓▓▓▓▓░░░░▒▒▒▒                    │  ← where the money went, one bar
├──────────────────────────────────────────────┤
│ ● Income                          $3,200  [+]│
│   Salary                          $3,000   × │
│   Freelance                         $200   × │
├──────────────────────────────────────────────┤
│ ● Necessities           $1,710 of $1,800  [+]│
│   ██████████████████████████░  Near limit    │  ← meter, only when a limit is set
│   Rent                            $1,200   × │
│   Groceries                         $380   × │
│   Gas                               $130   × │
├──────────────────────────────────────────────┤
│ ● Discretionary            $250 of $300   [+]│
│ ● Travel                     $0 of $200   [+]│
│   No trips yet. Add flights, hotels, food.   │  ← empty state, one line
├──────────────────────────────────────────────┤
│ ● Investments                        $640    │
│   Savings goal: $1,920 of $5,000             │
│   ███████████░░░░░░░░░░░░░░░░░░              │
└──────────────────────────────────────────────┘
```

**+** opens an inline row inside that section: `[Name] [Amount] [Add] [Cancel]`. **×** deletes a line.
If expenses exceed income, Investments reads **"Over budget by $85"** in the over-limit color and the
hero says the same.

### Account

- Display name, change password, sign out
- Monthly limits: overall, necessities, discretionary, travel (blank = no limit, no meter)
- Savings goal (amount)
- Delete my data (asks to confirm)

## 3. Code structure

Four modules, one owner each, so teammates rarely edit the same file.

```
sliced-bread/
  app.py            Gradio UI: sign-in, Budget tab, Account tab. Only file that imports gradio.
  budget.py         Pure logic: totals, leftover, meter state, savings progress, input validation
  storage.py        Read/write JSON; accounts with salted hashlib passwords
  design.py         The design system in code: Gradio theme + one CSS string
  test_budget.py    pytest for budget.py and storage.py
  requirements.txt  gradio (pinned to the version Colab ships)
  run_in_colab.ipynb  Two-cell launcher
  README.md         How to run, locally and in Colab
  data/             Per-user JSON (git-ignored)
```

**Data** — one JSON file per user, money kept in whole cents (ints) so totals never drift:

```json
{
  "settings": {"savings_goal": 500000,
               "limits": {"overall": 250000, "necessities": 180000, "discretionary": 30000, "travel": 20000}},
  "months": {"2026-10": {"income": [{"name": "Salary", "amount": 300000}],
                          "necessities": [], "discretionary": [], "travel": []}}
}
```

Investments are never stored; they're always computed. Savings progress = sum of positive leftovers
across all months.

**Gradio specifics** — `gr.Blocks` + `gr.State` for the signed-in user; each section's lines rendered
with `@gr.render` so the list grows and shrinks; `demo.launch(share=True)` when running in Colab so the
class demo gets a public link.

**Python concepts shown** (for the presentation): variables and constants, conditionals (alerts,
validation), loops (totals), functions, dicts/lists, file I/O (JSON), modules (`json`, `hashlib`,
`datetime`, `os`), exceptions (bad input), and a third-party library (Gradio).

## 4. Working across Claude Code and Colab

**Recommendation: GitHub is the single source of truth. Colab only pulls and runs.**

1. Code lives in a GitHub repo. I write and test it here, push it, the team pulls.
2. `run_in_colab.ipynb` has two cells:
   ```python
   # Cell 1 — get the latest code
   !git clone https://github.com/<you>/sliced-bread.git 2>/dev/null || git -C sliced-bread pull
   %cd sliced-bread
   !pip -q install -r requirements.txt
   ```
   ```python
   # Cell 2 — run it (prints a public *.gradio.live link)
   !python app.py
   ```
3. Re-run both cells after any change. No copy-pasting between tools.
4. Colab wipes files when the runtime resets. Optional third cell mounts Google Drive and points
   `DATA_DIR` there so demo accounts survive.
5. Teammates who prefer Colab + Gemini can still edit: open the file in GitHub's web editor (press `.`
   on the repo page), commit, then re-run the Colab cells. Never edit only the Colab copy — it's lost
   on reset.

Repo visibility: public is simplest for Colab. A private repo needs each teammate to add a read-only
GitHub token to Colab Secrets — doable, one extra step. **OWNER TO CONFIRM.**

Fallback if GitHub is a no-go: a single `sliced_bread.py` you paste into one Colab cell. Works, but
four people editing one pasted file will collide.

Note: this folder currently sits inside a git repo rooted at `C:\Users\markg`. Step 0 is `git init`
inside `Sliced Bread` so the project has its own repo.

## 5. Design system — "Toast"

Borrowed on purpose: **Propolis's** one-meaningful-accent rule and paper-and-ink base, **Pratt's**
quiet-screen and copy rules. Lives in `design.py`; nothing in `app.py` sets a color or size by hand.

### The one rule: crust means *you can press it*

Crust (the toasted accent) marks controls: the **+** buttons, the primary button, focus rings, the
active tab. It never marks money, status, or body text.

### Color

| Token | Hex | Use |
|---|---|---|
| `paper` | `#FAF8F4` | Page background |
| `card` | `#FFFFFF` | Section cards |
| `ink` | `#1F1D1A` | All text, all money |
| `muted` | `#6B655C` | Secondary labels (5.4:1 on paper) |
| `line` | `#E7E2D9` | Borders, dividers, empty meter track |
| `crust` | `#9A5B1E` | Controls, focus ring (white text on it: 5.4:1) |
| `crust-soft` | `#F6EBDD` | Hover/wash behind the inline add row |
| `good` | `#2F7D4F` | Meter fill under 90%, savings bar |
| `warn` | `#D99A00` | Meter fill 90–100% |
| `over` | `#B42318` | Meter fill over 100%, "Over budget" text |

Section dots and the stacked bar (fills only, never text): income `ink`, necessities `#3B6FB5`,
discretionary `#8E4FA8`, travel `#1E8C93`, investments `good`.

Status never relies on color alone: the meter always carries words ("Near limit", "Over by $45").

### Type

- **Inter** for text, **JetBrains Mono** with tabular numbers for every dollar amount, so columns align.
- One scale: 14 / 16 / 20 / 24 / 32 / 40 px. The hero is 40, or 32 on a phone. Nothing under 14 px except chips.
- Sentence case everywhere. No exclamation marks.

### Space and shape

- Spacing steps: 4 / 8 / 12 / 16 / 24 / 32 px. Section cards: 16 px padding, 12 px gap between.
- Radius: 8 px inputs and buttons, 12 px cards, pill for **+** and chips.
- One shadow, on cards only: `0 1px 2px rgb(0 0 0 / 0.06)`.
- One column, 640 px max, centered. Works at 375 px phone width with no sideways scroll.

### Copy (from Pratt's "quiet screens")

- **The title states the answer**, not the topic: "$640 left to invest in October", not "Summary".
- **One hero number per screen.**
- Labels are 1–3 words. Empty states are one line that says what to add.
- **No small print.** If a screen needs explaining, it's too complicated; fix the screen.

## 6. Build order

| Step | Done when |
|---|---|
| 0. Repo + Colab launcher | `git init`, GitHub repo, notebook runs a "hello" Gradio page in Colab |
| 1. `budget.py` + tests | Totals, leftover, meter states, validation pass `pytest` |
| 2. `storage.py` + tests | Create account, sign in, save/load a month round-trips |
| 3. `design.py` | Theme + CSS render on a blank Blocks page |
| 4. Budget tab | Five sections, add/delete, hero + bar, month picker |
| 5. Account tab | Limits, savings goal, password change, sign out |
| 6. Check | Tests pass; clicked through at 375 px and desktop; runs from a fresh Colab |

Validation handled in step 1: empty names, non-numbers, negatives, zero, more than 2 decimals, absurd
amounts (> $10M), duplicate usernames, wrong password.

## 7. Timeline and roles

Due date unknown — weeks below assume ~5 weeks. **OWNER TO CONFIRM the real dates and names.**

| Week | Milestone |
|---|---|
| 1 (Nov 2–8) | Stage 1 doc finished; repo + Colab launcher working; everyone can run it |
| 2 (Nov 9–15) | Logic, storage, accounts done with tests |
| 3 (Nov 16–22) | Full UI with design system; feature complete |
| 4 (Nov 23–29) | Testing round: normal + error scenarios, bug fixes, limitations written up |
| 5 (Nov 30–Dec 6) | Slides, 10-min demo script, rehearsal, submission |

| Member | Owns |
|---|---|
| A (you) | `app.py` + integration, Colab launcher, final demo |
| B | `budget.py`: calculations, alerts, validation |
| C | `storage.py`: accounts, JSON files, Drive persistence |
| D | `design.py` + summary bar; UI review at phone and desktop width |
| E | `test_budget.py`, test-scenario log, README, slides |

With 4 members, A takes D's work.

## 8. Later, not now

- **Robinhood referral** — a "Start investing" link in the Investments section. The "$50 per person"
  figure is unverified; Robinhood's referral terms change and may pay in stock, not cash. Needs a
  "not financial advice" line. **OWNER TO CONFIRM** before it's built.
- Gemini-written monthly tips (Colab has Gemini access) — good "future enhancement" slide.
- Recurring items (copy rent forward each month), CSV export, charts over time.

## Known limitations (to state in the presentation)

- Accounts are local JSON with hashed passwords — fine for a class demo, not real security.
- Colab data disappears on runtime reset unless Drive is mounted.
- One currency (USD); no bank sync.
