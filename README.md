# Sliced Bread

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sourypink/Sliced-Bread/blob/main/Sliced_Bread.ipynb)

A personal budget tracker in Python and Gradio. Add your income and spending; it tells you how much is
left to save each month, warns you near and over your limits, checks your split against one of three
research-backed plans (or your own), and tracks a savings goal.

Money goes into four fixed **categories** (Needs, Wants, Investing, Savings). Each category holds
**subcategories**: Necessities, Discretionary, Travel, Investments and Emergency fund to start, plus any you add on
the Goals tab and place in one of the four. Each subcategory holds **items**, like Rent. A small marker on every card
shows which category it counts toward.

## Run it in Google Colab

1. Click **Open in Colab** at the top of this page. It always opens the latest version from GitHub. The repo
   is private, so the first time Colab asks you to authorize GitHub: tick "Include private repos". Or
   download `Sliced_Bread.ipynb` and use File > Upload notebook in Colab.
2. Runtime > Run all. The app appears inside the last cell, with a public `gradio.live` link above it.

After a push, open the link again rather than re-running a Colab tab you already had open: that tab keeps the
old copy. If Colab still shows old code, use Runtime > Disconnect and delete runtime first.

The notebook holds every source file as a visible cell, so it is also the copy to hand in. It needs no
`git clone` and no Google Drive access.

Colab forgets files when the runtime resets, so saved budgets last only for that session.

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
| `app.py` | The Gradio screens: log in and create account, the Budget, History and Goals tabs, and the profile page. The only file that uses Gradio. |
| `budget.py` | The math: categories and subcategories, totals, what's left, limit and target alerts, input checks. |
| `storage.py` | Saves each account's budget as a JSON file named by its email, with a salted password hash. |
| `charts.py` | The History tab's chart (categories, then a subcategory, then its items), tiles and table, in plain HTML. |
| `design.py` | "Pond", the design system: colours, type, spacing, the Gradio theme, CSS and the mallard mascot. |
| `test_budget.py` | Tests for `budget.py` and `storage.py`. |
| `build_notebook.py` | Rebuilds `Sliced_Bread.ipynb` from the files above. |
| `Sliced_Bread.ipynb` | The Colab notebook: all the code, the tests and the running app. |
| `PLAN.md` | The plan: features, screens, design system, timeline and roles. |

Money is stored in whole cents so totals never drift. Savings are never stored: they are what you set aside
in Savings subcategories plus whatever is left of income.

## Known limitations

- Accounts are local: email and a salted password hash live in the same JSON file as the budget. Fine for a class
  demo, not for real money: there is no server-side account system, email verification, rate limiting or
  password reset.
- In Colab, saved budgets disappear when the runtime resets.
- US dollars only; no bank connection; no recurring items yet (rent must be added each month).
