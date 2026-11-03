"""Build Sliced_Bread.ipynb: every source file as a visible Colab cell. Run after changing any .py file."""

import json

NOTEBOOK = "Sliced_Bread.ipynb"
PREVIEW_HEIGHT = 900  # px, the app's frame inside the notebook

# (file, what it is), in the order a reader should meet them.
SOURCE_FILES = [
    ("budget.py", "The math: totals, what is left to invest, limit and target alerts, input checks. No Gradio here."),
    ("storage.py", "Accounts (salted, hashed passwords) and saving each user's budget as a JSON file."),
    ("design.py", "Toast, the design system: colours, type sizes, spacing, the Gradio theme and the CSS."),
    ("charts.py", "The History tab's chart, tiles and table, built from plain HTML so labels stay readable on a phone."),
    ("app.py", "The Gradio screens: sign in, the Budget tab and the Account tab. The only file that uses Gradio."),
    ("test_budget.py", "Automated tests for budget.py and storage.py."),
]

INTRO = """# Sliced Bread: a personal budget tracker

Add your income and spending; the app shows how much is left to invest each month, warns you near and over
your limits, compares your split with targets like 50/30/20, and tracks a savings goal.

**To run it:** Runtime > Run all. The app opens at the bottom of this notebook. A public `gradio.live`
link is printed above it as well.

Every source file is below as its own cell. Each cell starts with `%%writefile`, which saves the cell as
that `.py` file so the files can import each other. This notebook is generated from the files in
[github.com/sourypink/Sliced-Bread](https://github.com/sourypink/Sliced-Bread) by `build_notebook.py`."""

DRIVE = """# Optional: keep accounts and budgets in Google Drive so they survive a runtime reset.
# Uncomment and run before the last cell.
# from google.colab import drive
# import os
# drive.mount("/content/drive")
# os.environ["SLICED_BREAD_DATA"] = "/content/drive/MyDrive/sliced-bread-data"
"""

RUN = f"""# Start the app. Run this cell again after changing any file above.
import sys
import gradio as gr

gr.close_all()  # stop a copy started earlier in this session
for module in ("budget", "storage", "design", "charts", "app"):
    sys.modules.pop(module, None)  # re-import so edits to the cells above take effect

import app
import design

app.demo.launch(theme=design.build_theme(), css=design.CSS, head=design.HEAD, share=True, height={PREVIEW_HEIGHT})"""


def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


def build():
    with open("requirements.txt", encoding="utf-8") as file:
        packages = " ".join(line.strip() for line in file if line.strip())
    cells = [markdown(INTRO), code(f"# Install the exact versions the app was tested with.\n!pip -q install {packages}")]
    for file_name, description in SOURCE_FILES:
        with open(file_name, encoding="utf-8") as file:
            source = file.read()
        cells.append(markdown(f"## `{file_name}`\n\n{description}"))
        cells.append(code(f"%%writefile {file_name}\n{source}"))
    cells.append(markdown("## Run the tests\n\nEvery line should pass."))
    cells.append(code("!python -m pytest -q test_budget.py"))
    cells.append(markdown("## Run the app"))
    cells.append(code(DRIVE))
    cells.append(code(RUN))
    notebook = {
        "cells": cells,
        "metadata": {"colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 0,
    }
    with open(NOTEBOOK, "w", encoding="utf-8", newline="\n") as file:
        json.dump(notebook, file, indent=1, ensure_ascii=False)
    print(f"Wrote {NOTEBOOK} with {len(SOURCE_FILES)} source files")


if __name__ == "__main__":
    build()
