# Sliced Bread

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sourypink/Sliced-Bread/blob/main/Sliced_Bread.ipynb)

A personal budget tracker in Python and Gradio. Add your income and spending; it tells you how much is
left to save each month after spending and investing (grouped into tiers you name), warns you near and
over your limits, checks your split against targets like 50/30/20, and tracks a savings goal.

## Run it in Google Colab

1. Click **Open in Colab** at the top of this page. It always opens the latest version from GitHub.
2. Runtime > Run all. The app appears inside the last cell, with a public `gradio.live` link above it.

After a push, open the link again rather than re-running a Colab tab you already had open: that tab keeps the
old copy. If Colab still shows old code, use Runtime > Disconnect and delete runtime first.

The notebook holds every source file as a visible cell, so it is also the copy to hand in.

Colab forgets files when the runtime resets. To keep saved budgets between sessions, uncomment the Google
Drive cell before running the last cell.

**Workflow:** the `.py` files in this repo are the source. After changing one, run
`python build_notebook.py` to rebuild `Sliced_Bread.ipynb`, then commit both. Edits made only inside
Colab are lost unless you copy them back into the `.py` file.

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
| `storage.py` | Saves each name's budget as a JSON file. Demo mode: no passwords. |
| `charts.py` | The History tab's column chart, tiles and table, in plain HTML. |
| `design.py` | "Pond", the design system: colours, type, spacing, the Gradio theme, CSS and the mallard mascot. |
| `test_budget.py` | Tests for `budget.py` and `storage.py`. |
| `build_notebook.py` | Rebuilds `Sliced_Bread.ipynb` from the files above. |
| `Sliced_Bread.ipynb` | The Colab notebook: all the code, the tests and the running app. |
| `PLAN.md` | The plan: features, screens, design system, timeline and roles. |

Money is stored in whole cents so totals never drift. Savings aren't stored: they're always income
minus spending and investing.

## Known limitations

- Demo mode: any name and password sign in, and anyone who types your name sees your budget.
- In Colab, data disappears on a runtime reset unless Google Drive is mounted.
- US dollars only; no bank connection; no recurring items yet (rent must be added each month).
