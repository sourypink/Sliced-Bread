"""Build Sliced_Bread.ipynb: every source file as a visible Colab cell. Run after changing any .py file."""

import json

NOTEBOOK = "Sliced_Bread.ipynb"
PREVIEW_HEIGHT = 900  # px, the app's frame inside the notebook

# (file, what it is), in the order a reader should meet them.
SOURCE_FILES = [
    ("budget.py", "The math: categories and subcategories, totals, what is left, limit and target alerts, input checks. No Gradio here."),
    ("storage.py", "Saves each name's budget as a JSON file, with a salted hash of its password."),
    ("design.py", "Pond, the design system: colours, type, spacing, the Gradio theme, the CSS and the mallard mascot."),
    ("charts.py", "The History tab's chart, tiles and table: categories, then a subcategory, then its items. Plain HTML."),
    ("app.py", "The Gradio screens: sign in, the Budget, History and Goals tabs, and the profile page. The only file that uses Gradio."),
    ("test_budget.py", "Automated tests for budget.py and storage.py."),
]

INTRO = """# Sliced Bread: a personal budget tracker

Add your income and spending; the app shows how much is left to invest each month, warns you near and over
your limits, compares your split with a research-backed plan, and tracks a savings goal.

**To run it:** Runtime > Run all. The app opens at the bottom of this notebook, and a public `gradio.live`
link is printed above it (best for the class demo). If a button shows an error, run the last cell and share
what it prints.

Every source file is below as its own cell. Each cell starts with `%%writefile`, which saves the cell as
that `.py` file so the files can import each other. This notebook is generated from the files in
[github.com/sourypink/Sliced-Bread](https://github.com/sourypink/Sliced-Bread) by `build_notebook.py`."""

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

LOG = """# If a button shows an error, run this and send the output: it is the app's own log.
!tail -n 60 app.log"""


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
    cells.append(code(RUN))
    cells.append(code(LOG))
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
