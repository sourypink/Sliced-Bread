"""Build Sliced_Bread.ipynb: every source file, split into its sections, one Colab cell each. Run after changing any .py file."""

import json
import re

NOTEBOOK = "Sliced_Bread.ipynb"
PREVIEW_HEIGHT = 900  # px, the app's frame inside the notebook
SECTION_MARKER = re.compile(r"^[ \t]*# ---------- (.+) ----------\n", re.MULTILINE)
PREAMBLE = "Imports and settings"  # the title of the part of a file before its first marker

# The numbered parts of the notebook, in the order a reader should meet them: (file, heading, what it is).
PARTS = [
    ("budget.py", "Calculations", "All the money math: categories and subcategories, totals, what is left, percentage targets and history. No screens here, so it can be tested on its own."),
    ("storage.py", "Saving accounts", "Each account is one JSON file named by its email, with a salted hash of its password instead of the password."),
    ("design.py", "Design", "Pond, the design system: colours, type, spacing, the Gradio theme, the CSS and the mallard mascot."),
    ("charts.py", "Charts", "The History tab's chart, tiles and table, built as plain HTML from the numbers in budget.py."),
    ("app.py", "App screens", "The Gradio screens: log in, the Budget, History and Goals tabs, pop-ups and the profile page. The only file that uses Gradio."),
]
BUILDER = "build_notebook.py"

# One line under each section's heading, by (file, section title). Every section needs one: the build stops if it's missing.
NOTES = {
    ("budget.py", PREAMBLE): "The four fixed categories, the starting subcategories, the three research-backed plans, and the limits on what can be typed.",
    ("budget.py", "Checking what the user typed"): "Turn typed amounts into whole cents and names into clean text, or raise a ValueError that says what is wrong.",
    ("budget.py", "Subcategories"): "Add, rename, move and remove subcategories. Each keeps a fixed key so past months stay attached.",
    ("budget.py", "Totals"): "Sums per section and category, what is left of income, and what was saved.",
    ("budget.py", "Lines"): "Add, edit and delete one line in a month.",
    ("budget.py", "Percentage targets"): "The four shares of income that must add up to 100, the box that fills itself in, and how each category compares.",
    ("budget.py", "Months"): "Month keys like 2026-10, moving between months, and their names.",
    ("budget.py", "History"): "One row of totals per month for the History tab, and sample months for demos.",
    ("storage.py", PREAMBLE): "Where files go (set SLICED_BREAD_DATA to change it) and the rules for names, emails and passwords.",
    ("storage.py", "Names and saved files"): "Clean a person's name, and load, save, rename and delete their budget file.",
    ("storage.py", "Passwords"): "Salted PBKDF2 hashes, compared in constant time.",
    ("storage.py", "Accounts"): "Check an email, create an account, and log in.",
    ("design.py", PREAMBLE): "What this file is and what it imports.",
    ("design.py", "Tokens"): "Every colour, size and font the app uses, with why. Category colours avoid red, orange and green.",
    ("design.py", "Scripts the page runs"): "Small browser scripts: $ and commas as you type, and clicks on the History chart.",
    ("design.py", "The Gradio theme"): "Gradio's built-in theme, set to the tokens above.",
    ("design.py", "The CSS"): "Cards, buttons, meters, the donut and the pop-ups.",
    ("design.py", "The mallard"): "The duck mascot as SVG: a detailed one for sign-in and a simple mark for the header.",
    ("design.py", "HTML pieces (escape everything the user typed)"): "Reusable bits of HTML: the donut, category markers, meters and lines.",
    ("charts.py", PREAMBLE): "Chart settings: tick steps, label spacing, and how many items to name.",
    ("charts.py", "What a zoom level shows"): "Which pieces the chart stacks when you zoom from categories into a subcategory and its items.",
    ("charts.py", "The chart"): "The column chart itself: earned beside money out for each month, with tooltips and a legend.",
    ("charts.py", "Tiles, table and biggest items"): "The four totals above the chart, the table of every number, and the biggest lines.",
    ("app.py", PREAMBLE): "Imports, placeholder text, and helpers every handler uses to save a change or show an error.",
    ("app.py", "Page pieces"): "The HTML for the duck's line, the hero card (big number, donut and split), each section and the Savings card.",
    ("app.py", "Event handlers: lines"): "What happens when you add, edit or delete a line.",
    ("app.py", "Event handlers: subcategories"): "What happens when you add, rename, move or remove a subcategory.",
    ("app.py", "Event handlers: goals"): "Saving your split, picking a preset plan, and filling in the fourth box.",
    ("app.py", "Event handlers: history"): "Redrawing the History tab for a range or zoom, and filling sample months.",
    ("app.py", "Event handlers: account"): "Log in, create an account, sign out, edit the profile, change the password, delete my data.",
    ("app.py", "Layout: log in"): "The screen's state, then the log-in and create-account card.",
    ("app.py", "Layout: header and Budget tab"): "The header with the avatar menu, and the Budget tab: hero card, every section, and Savings.",
    ("app.py", "Layout: History tab"): "Range pills, sample-month offer, tiles, chart and biggest items.",
    ("app.py", "Layout: Goals tab"): "Your split (four percentages) and the button that opens the subcategory editor.",
    ("app.py", "Layout: pop-ups"): "The subcategory editor and the plan chooser.",
    ("app.py", "Layout: profile page"): "Name and email, password change, and delete my data.",
    ("app.py", "Wiring"): "Connects every button and box to its handler, and starts the app when run as a program.",
}

INTRO = """# Sliced Bread: a personal budget tracker

Add your income and spending; the app shows how much is left to save each month, splits it into Needs, Wants,
Investing and Savings, and compares that split with a plan you choose (like 50/30/15/5).

**To run it:** Runtime > Run all. The app opens under section 7, with a public `gradio.live` link above it.

**How the code is laid out:** each source file is split into its sections, one cell each. The first cell of a
file starts with `%%writefile`, which saves the cell as that `.py` file; the rest start with `%%writefile -a`,
which adds to it. That way the files can import each other and the tests can run, while every line is here to read.

1. Setup
2. Calculations (`budget.py`)
3. Saving accounts (`storage.py`)
4. Design (`design.py`)
5. Charts (`charts.py`)
6. App screens (`app.py`)
7. Run the app"""

# The app runs in its own Python process, not inside this notebook's: a fresh process always uses the packages
# the install cell just put on disk, even if this notebook loaded older ones earlier. Its output goes to app.log.
RUN = f"""# Start the app. Run this cell again after changing any file above.
import re
import subprocess
import sys
import time

STARTUP_SECONDS = 90  # the public link can take a while to appear

if "server" in globals() and server.poll() is None:
    server.terminate()  # stop the copy started earlier in this session
    server.wait()

log = open("app.log", "w")
server = subprocess.Popen([sys.executable, "-u", "app.py", "--share"], stdout=log, stderr=subprocess.STDOUT)
for _ in range(STARTUP_SECONDS):
    time.sleep(1)
    started = open("app.log").read()
    if "public URL" in started or "share link" in started.lower() or server.poll() is not None:
        break
print(started)
if server.poll() is not None:
    raise RuntimeError("The app stopped while starting. The error is printed above.")

port = re.search(r"127\\.0\\.0\\.1:(\\d+)", started)
try:
    from google.colab import output
    output.serve_kernel_port_as_iframe(int(port.group(1)) if port else 7860, height={PREVIEW_HEIGHT})
except ImportError:
    print("Not in Colab: open the local or public URL above.")"""


def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}


def sections(file_name):
    """A file as (title, text) pieces, split at its section markers. Joined back together they are the file."""
    with open(file_name, encoding="utf-8") as file:
        source = file.read()
    starts = [match.start() for match in SECTION_MARKER.finditer(source)]
    titles = [PREAMBLE] + SECTION_MARKER.findall(source)
    bounds = [0] + starts + [len(source)]
    return [(title, source[start:end]) for title, start, end in zip(titles, bounds, bounds[1:]) if source[start:end].strip()]


def file_cells(file_name, number=None):
    """Markdown and code cells for every section of a file; the code cells write it back out piece by piece."""
    cells = []
    for index, (title, text) in enumerate(sections(file_name)):
        if (file_name, title) not in NOTES:
            raise KeyError(f'Add a line for "{title}" in {file_name} to NOTES in {BUILDER}')
        heading = f"{number}.{index + 1} {title}" if number else title
        cells.append(markdown(f"### {heading}\n\n{NOTES[file_name, title]}"))
        # The piece exactly as it is in the file, blank lines included, so the written file matches GitHub's.
        cells.append(code(f"%%writefile {'-a ' if index else ''}{file_name}\n{text}"))
    return cells


def build():
    with open("requirements.txt", encoding="utf-8") as file:
        packages = " ".join(line.strip() for line in file if line.strip())
    cells = [
        markdown(INTRO),
        markdown("## 1. Setup\n\nInstall the exact package versions the app was tested with."),
        code(f"!pip -q install {packages}"),
    ]
    for number, (file_name, heading, description) in enumerate(PARTS, start=2):
        cells.append(markdown(f"## {number}. {heading} (`{file_name}`)\n\n{description}"))
        cells.extend(file_cells(file_name, number))
    cells += [
        markdown(f"## {len(PARTS) + 2}. Run the app"),
        code(RUN),
    ]
    notebook = {
        "cells": cells,
        "metadata": {"colab": {"provenance": [], "toc_visible": True}, "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 0,
    }
    with open(NOTEBOOK, "w", encoding="utf-8", newline="\n") as file:
        json.dump(notebook, file, indent=1, ensure_ascii=False)
    print(f"Wrote {NOTEBOOK} with {sum(cell['cell_type'] == 'code' for cell in cells)} code cells")


if __name__ == "__main__":
    build()
