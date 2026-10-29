# Sliced Bread

A personal budget tracker in Python and Gradio. Add your income and spending; it tells you how much is
left to invest each month, warns you near and over your limits, and tracks a savings goal.

## Run it in Google Colab

1. In Colab: File > Open notebook > GitHub, paste `sourypink/Sliced-Bread`, open `run_in_colab.ipynb`.
2. Run cell 1, then cell 2. Open the `gradio.live` link cell 2 prints.

Colab forgets files when the runtime resets. To keep accounts between sessions, run the optional Google
Drive cell before cell 2.

**Workflow:** GitHub holds the code. Edit there (or locally) and push; in Colab, stop cell 2 and run
both cells again. Edits made only inside Colab are lost on reset.

## Run it on your computer

```
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:7860. Add `--share` for a public link.

## Test it

```
python -m pytest
```

## How it's built

| File | What it does |
|---|---|
| `app.py` | The Gradio screens: sign in, Budget tab, Account tab. The only file that uses Gradio. |
| `budget.py` | The math: totals, what's left, limit alerts, savings progress, input checks. |
| `storage.py` | Accounts (salted, hashed passwords) and saving each user's budget as JSON. |
| `design.py` | "Toast", the design system: colours, type, spacing, the Gradio theme and CSS. |
| `test_budget.py` | 52 tests for `budget.py` and `storage.py`. |
| `PLAN.md` | The plan: features, screens, design system, timeline and roles. |

Money is stored in whole cents so totals never drift. Investments aren't stored: they're always income
minus spending.

## Known limitations

- Accounts live in local JSON files: fine for a class demo, not real security.
- In Colab, data disappears on a runtime reset unless Google Drive is mounted.
- US dollars only; no bank connection; no recurring items yet (rent must be added each month).
