# Sliced Bread — personal budget tracker (plan)

Python + Gradio. Runs the same way on a laptop and in Google Colab. Status: **draft, awaiting approval.**

## 1. What we're building

One question answered on one page: **how much do I have left to invest this month?**

Words, used the same way in code and on screen:

- **Category**: one of four, fixed forever: **Needs**, **Wants**, **Investing**, **Savings**. Targets and the
  History chart are built on these, so history stays comparable whatever else changes.
- **Subcategory**: Necessities (Needs), Discretionary and Travel (Wants), Investments (Investing), Emergency fund (Savings) to
  start, plus up to 8 of the user's own. Each sits in exactly one category; from the Goals tab any of them can be
  renamed or moved, and the user's own can be removed once they hold no items. A small marker ("● Wants") on every card
  says which category it counts toward, and its dot is a shade of that category's colour.
- **Item**: a line in a subcategory: Rent, Flights.

The page reads top to bottom, the way money flows: **Income**, then the subcategories grouped Needs → Wants →
Investing → Savings, then the **Savings** card: what was set aside in Savings subcategories plus whatever is left.

No default line items. Each section starts empty with one line of guidance and a **+** button.

Maps to the brief's feature list:

| Brief asks for | Where it lives |
|---|---|
| Income tracking | Income section, total at the top |
| Expense tracking (amount, category, description) | Sections 2–4; the section *is* the category, the line name is the description |
| Edit a line | ✎ on a line opens it in place; Save or Cancel |
| Overall + per-category budgets | Goals tab: one monthly limit; each category's limit is that times its % |
| Automatic calculations | `budget.py`; every add or delete recomputes |
| Budget alerts | Limit meters under the hero shift from green through amber to red as they fill: near limit at 90%, over at 100% |
| Monthly summary | The hero line and a donut of where the money went at the top of the page; month picker |
| Investing | Investments section: plain lines like any subcategory, counted toward Investing |
| Savings goal | Savings card: progress toward the goal set on the Goals tab |
| History over months | History tab: earned vs money out per month by category (6 / 12 months / All); click a category to see its subcategories, then a subcategory to see its items in shades of its colour; biggest items, a table of every number, and sample months for demos |
| Percentage targets (50/30/20) | Goals tab sets the four categories' % (typing three fills the fourth to make 100), or picks one of three cited presets, offered once at sign-up; a split card under the hero compares actual vs target and alerts on overspend |
| Own categories | Goals tab: add a subcategory and pick which of the four categories it counts toward; the presets can be removed too |
| Accounts | Create an account (name, email, password) and log in with email and password (salted hash); the avatar menu has Edit profile (name, email, password, delete my data) and Sign out |

## 2. Screens

Three tabs after sign-in: **Budget** (landing), **History** and **Goals**, plus a **Profile** page opened from the
avatar menu. Before log-in, only the log-in card.

### Log in / Create account

```
┌──────────────────────────────┐   ┌──────────────────────────────┐
│ Sliced Bread                 │   │ Create an account            │
│ Log in                       │   │ Name           [          ]  │
│ Email    [            ]      │   │ Email          [          ]  │
│ Password [            ]      │   │ Password       [          ]  │
│ [ Log in ]                   │   │ Password again [          ]  │
│ New here? Create an account  │   │ [ Create account ]           │
└──────────────────────────────┘   │ Have an account? Log in      │
                                   └──────────────────────────────┘
```

Accounts are local JSON files, not a real auth service: no email is ever sent.

### Budget (landing) — one centered column, 640 px max

```
┌──────────────────────────────────────────────┐
│ $640 left to invest in October      Oct 2026▾│  ← hero: title states the answer
│ ( donut )  ● Needs $1,710  ● Wants $250 ...  │  ← where the money went, a donut and its key
├──────────────────────────────────────────────┤
│ ● Income                          $3,200  [+]│
│   Salary                          $3,000   × │
│   Freelance                         $200   × │
├──────────────────────────────────────────────┤
│ ● Necessities                     $1,710  [+]│
│   Rent                            $1,200   × │
│   Groceries                         $380   × │
│   Gas                               $130   × │
├──────────────────────────────────────────────┤
│ ● Discretionary                     $250  [+]│
│ ● Travel                              $0  [+]│
│   No trips yet. Add flights, hotels, food.   │  ← empty state, one line
├──────────────────────────────────────────────┤
│ ● Investments                        $640    │
│   Savings goal: $1,920 of $5,000             │
│   ███████████░░░░░░░░░░░░░░░░░░              │
└──────────────────────────────────────────────┘
```

**+** opens an inline row inside that section: `[Name] [Amount] [Add] [Done]`; the + hides while it's open. **×** deletes a line.
If expenses exceed income, Investments reads **"Over budget by $85"** in the over-limit color and the
hero says the same.

### History

- Range pills: 6 months, 12 months, All.
- Four tiles for the range: earned, spent, invested, saved. When zoomed: the total, monthly average, share of income.
- Column chart per month: earned beside money out, stacked by the four categories. Click a colour (or its legend
  entry) to zoom: a category splits into its subcategories (Savings adds "Left over"), and a subcategory splits
  into its biggest items, darkest at the bottom, in shades of its colour. A back link climbs one level.
- Biggest items in the zoomed view, and "See the numbers" opens a table with every value.
- Under three months of data, the duck offers "Fill 5 sample months": fixed demo data, tagged "(sample)", only
  in empty months before this one.

### Goals

- **Your plan**: Monthly limit first, then the four categories' %. Needs and wants are limits; investing and
  savings are minimums. Typing three fills the fourth to make 100. A line under the boxes shows each % in dollars
  of the limit ("Needs $1,500 · Wants $900 ..."), and those are the Needs and Wants limits the hero's meters use.
  With targets off, the limit caps all spending.
- **Choose a preset** opens "Pick a plan": three presets, each with the research behind it.
  Picking one keeps the Monthly limit set on Goals.
  A new account sees it once after its first sign-in; "Set my own" closes it for good.

  | Preset | Needs/Wants/Investing/Savings | Basis |
  |---|---|---|
  | Balanced | 50/30/15/5 | Warren & Tyagi, *All Your Worth* (2005), 50/30/20; Fidelity's 50/15/5 saving guideline |
  | Safety net first | 50/20/10/20 | Vanguard (2025, 12,400 investors): $2,000+ in emergency savings, 21% higher financial well-being |
  | Invest more | 45/20/30/5 | Fidelity: save more than 15% to retire before 67; Bengen (1994), the 4% rule: 25x yearly spending |

- "Edit subcategories" opens a pop-up, grouped under each category's marker: rename and move with a category
  picker, saved together on Confirm (Cancel discards). ✕ removes any subcategory, presets included (tagged
  "Preset"), only when empty; it and the add row (name and the category it counts toward) save straight away.
- Savings goal, in its own card.
- Every amount box shows $ and commas as you type.

### Profile (avatar menu, then Edit profile)

- Name and email (the log-in email; changing it moves the saved file); change password (current, new, again); delete my data (asks to
  confirm). Replaces the tabs until "← Back"; Sign out is in the same menu.

## 3. Code structure

Four modules, one owner each, so teammates rarely edit the same file.

```
sliced-bread/
  app.py            Gradio UI: sign-in, Budget, History and Goals tabs, profile. Only file that imports gradio.
  budget.py         Pure logic: totals, leftover, meter state, savings progress, input validation
  storage.py        Read/write one JSON budget per account email, with a salted PBKDF2 password hash
  design.py         The design system in code: Gradio theme + one CSS string
  charts.py         History tab: column chart, tiles, table (plain HTML, no Gradio)
  test_budget.py    pytest for budget.py and storage.py
  requirements.txt  gradio (pinned to the version Colab ships)
  run_in_colab.ipynb  Two-cell launcher
  README.md         How to run, locally and in Colab
  data/             Per-user JSON (git-ignored)
```

**Data** — one JSON file per user, money kept in whole cents (ints) so totals never drift:

```json
{
  "account": {"name": "Mark", "email": "mark@example.com", "salt": "(hex)", "password_hash": "(hex)"},
  "settings": {"savings_goal": 500000,
               "limits": {"overall": 300000},
               "targets": {"needs": 50, "wants": 30, "investing": 15, "savings": 5},
               "plan_chosen": true, "removed_presets": ["travel"],
               "subcategories": [{"key": "necessities", "name": "Necessities", "category": "needs"},
                                 {"key": "pets", "name": "Pets", "category": "wants"}]},
  "months": {"2026-10": {"income": [{"name": "Salary", "amount": 300000}],
                          "necessities": [], "pets": [{"name": "Vet", "amount": 6000}]}}
}
```

A subcategory's key never changes (a rename only changes its name), so past months stay attached. Budgets saved
before subcategories, or before a starting one was added, get the missing starting ones. Savings are never stored; they're always computed: set aside in
Savings subcategories plus whatever is left of income.

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
| `accent-soft` | `#E7F1EA` | Add/edit panel, Savings card |
| `warn` | `#D99A00` | Meter fill 90–100% |
| `over` | `#B42318` | Meter fill over 100%, "Over budget" amount |

Section dots, bars and chart columns (fills only): income and savings `accent`, investments `#6250D6`, necessities `#2A78D6`,
discretionary `#EB6834`, travel `#1BAF7A`; unpicked categories in a zoomed chart `#D9D4CA`. Checked with the
dataviz palette validator (all pairs pass, including colour-blind separation); the earlier blue and purple
did not. The duck has its own colours and they are used nowhere else.

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
| 5. Goals tab + profile | Limits, savings goal, targets, subcategories; profile, password, sign out, delete my data |
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

- Passwords are hashed, but they live in the same JSON file as the budget, and there is no email verification,
  rate limiting or password reset. Fine for a class demo, not for real money.
- Colab data disappears on runtime reset unless Drive is mounted.
- One currency (USD); no bank sync.
