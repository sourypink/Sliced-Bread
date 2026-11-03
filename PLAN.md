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
| Edit a line | ✎ on a line opens it in place; Save or Cancel |
| Overall + per-category budgets | Account page: one limit per section, plus an overall monthly limit |
| Automatic calculations | `budget.py`; every add or delete recomputes |
| Budget alerts | A meter under each section: near limit at 90%, over at 100% |
| Monthly summary | The hero line and stacked bar at the top of the page; month picker |
| Savings goal | Investments section: progress toward the goal set on the account page |
| Percentage targets (50/30/20) | Account page sets needs/wants/savings %; a split card under the hero compares actual vs target and alerts on overspend |

## 2. Screens

Two screens after sign-in, as tabs: **Budget** (landing) and **Account**. Before sign-in, only the sign-in card.

### Sign in

```
┌──────────────────────────────┐
│ Sliced Bread                 │
│ Know what's left each month  │
│                              │
│ Name     [            ]      │
│ Password [ anything   ]      │
│ [ Sign in ]                  │
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

- Sign out
- Monthly limits: overall, necessities, discretionary, travel (blank = no limit, no meter)
- Savings goal (amount)
- Percentage targets: needs (necessities), wants (discretionary + travel), savings (what is left); "Use 50/30/20" fills and saves them
- Delete my data (asks to confirm)

## 3. Code structure

Four modules, one owner each, so teammates rarely edit the same file.

```
sliced-bread/
  app.py            Gradio UI: sign-in, Budget tab, Account tab. Only file that imports gradio.
  budget.py         Pure logic: totals, leftover, meter state, savings progress, input validation
  storage.py        Read/write one JSON budget per name (demo mode: no passwords)
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
   `DATA_DIR` there so saved budgets survive.
5. Teammates who prefer Colab + Gemini can still edit: open the file in GitHub's web editor (press `.`
   on the repo page), commit, then re-run the Colab cells. Never edit only the Colab copy — it's lost
   on reset.

Repo visibility: public is simplest for Colab. A private repo needs each teammate to add a read-only
GitHub token to Colab Secrets — doable, one extra step. **OWNER TO CONFIRM.**

Fallback if GitHub is a no-go: a single `sliced_bread.py` you paste into one Colab cell. Works, but
four people editing one pasted file will collide.

Note: this folder currently sits inside a git repo rooted at `C:\Users\markg`. Step 0 is `git init`
inside `Sliced Bread` so the project has its own repo.

## 5. Design system — "Pond"

Lives in `design.py`; nothing in `app.py` sets a colour or size by hand. Replaced "Toast" on 2026-11-03.

### The one rule: green means go

Mallard green marks what you can press (buttons, "+ Add", focus) and spending that is on track. Amber means near a
limit, red means over. Status never relies on colour alone: every meter carries words ("Near limit", "Over by $45").

### Colour

| Token | Hex | Use |
|---|---|---|
| `paper` | `#F4F2ED` | Page background, a shade darker than cards |
| `paper-deep` | `#E9E5DD` | Tab switcher track |
| `card` | `#FFFFFF` | Cards |
| `ink` | `#1C1B18` | All text, all money |
| `muted` | `#6B665D` | Labels (5:1 on paper) |
| `line` | `#E2DDD3` | Card borders, dividers, empty meter track |
| `field-border` | `#958D81` | Text box borders (3.3:1 on white) |
| `accent` | `#1F7A4D` | Buttons, focus, on-track meters (white text on it: 5.3:1) |
| `accent-dark` | `#17603C` | Button hover |
| `accent-soft` | `#E7F1EA` | Add/edit panel, Investments card |
| `warn` | `#D99A00` | Meter fill 90–100% |
| `over` | `#B42318` | Meter fill over 100%, "Over budget" amount |

Section dots and the stacked bar (fills only): income `ink`, necessities `#3B6FB5`, discretionary `#8E4FA8`,
travel `#1E8C93`, investments `accent`. The duck has its own colours and they are used nowhere else.

### Type

- **Instrument Serif** for the wordmark, card titles and the big numbers; **Geist** for everything else.
- Money uses Geist with tabular figures so columns line up.
- Scale: 14 / 16 / 20 / 26 / 40 / 64 px (the hero is 48 on a phone). Nothing under 14 px.
- Sentence case everywhere. No exclamation marks.

### Shape and space

- Radius: cards 20 px, inner panels 14 px, text boxes 12 px. Buttons are pills; icon buttons are circles.
- Card padding 20 px (24 px from 600 px wide); 16 px between cards.
- One soft shadow, on cards only. One centred column, 640 px max; works at 375 px with no sideways scroll.

### No backlights

No glows. Focusing a text box turns its border green; nothing lights up around it. Gradio's busy fade, accent
border and progress overlay are switched off. Keyboard focus keeps a thin 2 px green ring (accessibility).

### The mallard

- **Detailed** (`duck_full`): iridescent head, white neck ring, chestnut breast, grey body, blue-violet wing
  patch, on water. Used on the sign-in card, with a gentle bob (off when the system asks for reduced motion).
- **Logo** (`duck_mark`): flat colours, readable at 24 px. Used in the header and beside the hero's speech bubble.
- For now the duck only says one line under the hero (`duck_line` in `app.py`): add income, nice, careful, quack.

### Copy (from Pratt's "quiet screens")

- The big number states the answer; its label says what it is ("Left to invest in November").
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
| 5. Account tab | Limits, savings goal, targets, sign out, delete my data |
| 6. Check | Tests pass; clicked through at 375 px and desktop; runs from a fresh Colab |

Validation handled in step 1: empty names, non-numbers, negatives, zero, more than 2 decimals, absurd
amounts (> $10M), blank or symbol-only names.

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
| C | `storage.py`: saved budgets, JSON files, Drive persistence |
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

- Demo mode: any name and password sign in, and anyone who types your name sees your budget. Real accounts are future work.
- Colab data disappears on runtime reset unless Drive is mounted.
- One currency (USD); no bank sync.
