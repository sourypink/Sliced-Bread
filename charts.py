"""History charts for Sliced Bread: earned vs money out by month, and a zoom on one category. HTML only, no Gradio.

Built from plain HTML and CSS columns (not SVG) so labels stay readable at phone width. Follows the dataviz
rules: columns at most 24px wide with 4px rounded tops, 2px gaps between stacked pieces, hairline gridlines,
a legend, one callout above the plot, hover/keyboard details on every piece, and a table with every number.
"""

from html import escape

import budget
import design

SECTION_NAMES = {"necessities": "Necessities", "discretionary": "Discretionary", "travel": "Travel", "investments": "Investments"}
NICE_STEPS = (1, 2, 2.5, 5)  # tick steps, times a power of ten
TARGET_TICKS = 4  # gridlines above zero
HEADROOM = 1.12  # space above the tallest column for its label
COMPACT_FROM_CENTS = 10_000 * budget.CENTS_PER_DOLLAR  # axis switches to "$10K" style from here
# Month labels: show every Nth, counted back from the latest month, so they never run together.
LABEL_EVERY = ((12, 1), (24, 2))  # desktop: up to 12 months label all, up to 24 every other
PHONE_LABEL_EVERY = ((6, 1), (12, 2), (24, 4))  # phone widths fit about six labels


def nice_ceiling(cents):
    """The top of the y-axis and its step: a clean number just above the tallest column."""
    target = max(cents * HEADROOM, budget.CENTS_PER_DOLLAR) / TARGET_TICKS
    magnitude = 10 ** (len(str(int(target))) - 1)
    step = int(next(m * magnitude for m in NICE_STEPS + (10,) if m * magnitude >= target))
    return step * TARGET_TICKS, step


def tick_label(cents):
    dollars = cents / budget.CENTS_PER_DOLLAR
    if cents >= COMPACT_FROM_CENTS:
        return f"${dollars / 1000:g}K"
    return f"${dollars:,.0f}"


def full_month(key):
    return budget.month_label(key)


def money_out(row):
    """Spending plus investing: everything that left the month's income."""
    return row["spent"] + row["invested"]


def piece(value, color, label, is_top):
    """One stacked piece: hover title, keyboard focus and a screen-reader name carry its exact value."""
    radius = " sb-seg-top" if is_top else ""
    text = escape(label)
    return f'<div class="sb-seg{radius}" style="flex:{value};background:{color}" tabindex="0" title="{text}" aria-label="{text}"></div>'


def column(pieces, height_percent):
    """A column of stacked pieces, bottom piece first, as tall as height_percent of the plot."""
    shown = [p for p in pieces if p[0] > 0]
    if not shown:
        return ""
    inner = "".join(piece(value, color, text, index == len(shown) - 1) for index, (value, color, text) in enumerate(shown))
    return f'<div class="sb-stack" style="height:{height_percent:.2f}%">{inner}</div>'


def history_chart(rows, category):
    """Earned vs money out per month, or one category with everything else greyed out."""
    zoomed = category in SECTION_NAMES
    tallest = max((money_out(row) if zoomed else max(row["income"], money_out(row))) for row in rows)
    top, step = nice_ceiling(tallest)

    columns = []
    for row in rows:
        month = full_month(row["key"])
        if zoomed:
            others = money_out(row) - row["sections"][category]
            amount = row["sections"][category]
            spent = column(
                [(amount, design.SECTION_COLORS[category], f"{month} · {SECTION_NAMES[category]} {budget.format_money(amount)}"),
                 (others, design.MUTED_FILL, f"{month} · Everything else {budget.format_money(others)}")],
                money_out(row) / top * 100,
            )
            columns.append(f'<div class="sb-month-col">{spent}</div>')
            continue
        earned = column(
            [(row["income"], design.SECTION_COLORS["income"], f"{month} · Earned {budget.format_money(row['income'])}")],
            row["income"] / top * 100,
        )
        spent = column(
            [(row["sections"][section], design.SECTION_COLORS[section],
              f"{month} · {SECTION_NAMES[section]} {budget.format_money(row['sections'][section])}")
             for section in SECTION_NAMES],
            money_out(row) / top * 100,
        )
        columns.append(f'<div class="sb-month-col">{earned}{spent}</div>')

    grid = "".join(
        f'<div class="sb-grid" style="bottom:{value / top * 100:.2f}%"><span>{tick_label(value)}</span></div>'
        for value in range(0, top + 1, step)
    )
    count = len(rows)
    every = next(step for limit, step in LABEL_EVERY if count <= limit)
    phone_every = next(step for limit, step in PHONE_LABEL_EVERY if count <= limit)
    months = "".join(
        f'<span class="{label_classes(count - 1 - index, every, phone_every)}">{row["label"]}</span>'
        for index, row in enumerate(rows)
    )
    title = f"{SECTION_NAMES[category]} by month" if zoomed else "Earned vs spent and invested"
    span = full_month(rows[0]["key"]) if count == 1 else f"{full_month(rows[0]['key'])} to {full_month(rows[-1]['key'])}"
    best = best_month_html(rows, category)
    return (
        f'<div class="sb-title">{title}</div><div class="sb-note">{span}</div>{best}'
        f'<div class="sb-chart" role="group" aria-label="{escape(title)}, {escape(span)}">'
        f'<div class="sb-plot">{grid}<div class="sb-cols" style="grid-template-columns:repeat({count},minmax(0,1fr))">{"".join(columns)}</div></div>'
        f'<div class="sb-xaxis" style="grid-template-columns:repeat({count},minmax(0,1fr))">{months}</div></div>'
        f"{legend_html(category)}{numbers_table_html(rows, category)}"
    )


def best_month_html(rows, category):
    """The one callout: the month that stands out, above the chart so it never sits on a column."""
    if category in SECTION_NAMES:
        best = max(rows, key=lambda row: row["sections"][category])
        amount = best["sections"][category]
        text = f"Biggest month: {full_month(best['key'])}, {budget.format_money(amount)}"
    else:
        best = max(rows, key=lambda row: row["left"])
        amount = best["left"] if best["income"] else 0
        text = f"Best month: {full_month(best['key'])}, {budget.format_money(amount)} saved"
    return f'<div class="sb-callout">{text}</div>' if amount > 0 else ""


def label_classes(months_back, every, phone_every):
    """Which screens hide this month's label: it shows only on every Nth month back from the latest."""
    hidden = []
    if months_back % every:
        hidden.append("sb-hide-desktop")
    if months_back % phone_every:
        hidden.append("sb-hide-phone")
    return " ".join(hidden)


def legend_html(category):
    if category in SECTION_NAMES:
        entries = [(SECTION_NAMES[category], design.SECTION_COLORS[category]), ("Everything else", design.MUTED_FILL)]
    else:
        entries = [("Earned", design.SECTION_COLORS["income"])] + [(name, design.SECTION_COLORS[key]) for key, name in SECTION_NAMES.items()]
    items = "".join(f'<span><i style="background:{color}"></i>{name}</span>' for name, color in entries)
    return f'<div class="sb-legend">{items}</div>'


def stat_tiles_html(rows, category):
    """The range in numbers. Plain sans, proportional digits: these are standalone figures."""
    if category in SECTION_NAMES:
        name = SECTION_NAMES[category]
        total = sum(row["sections"][category] for row in rows)
        active = [row for row in rows if row["income"] or money_out(row)] or rows
        out = sum(money_out(row) for row in rows)
        share = f"{round(total * 100 / out)}%" if out else "0%"
        first = "Invested" if category == budget.TIERED_SECTION else f"Spent on {name.lower()}"
        tiles = [(first, budget.format_money(total), ""),
                 ("Monthly average", budget.format_money(total // len(active)), ""),
                 ("Share of money out", share, "")]
    else:
        earned = sum(row["income"] for row in rows)
        saved = sum(row["left"] for row in rows)
        tiles = [("Earned", budget.format_money(earned), ""),
                 ("Spent", budget.format_money(sum(row["spent"] for row in rows)), ""),
                 ("Invested", budget.format_money(sum(row["invested"] for row in rows)), ""),
                 ("Saved", budget.format_money(saved), " sb-over" if saved < 0 else "")]
    cells = "".join(
        f'<div class="sb-tile"><div class="sb-eyebrow">{label}</div><div class="sb-tile-value{extra}">{value}</div></div>'
        for label, value, extra in tiles
    )
    return f'<div class="sb-tiles sb-tiles-{len(tiles)}">{cells}</div>'


def numbers_table_html(rows, category):
    """Every number in the chart, as a table: the version that needs no hovering."""
    extra = category in SECTION_NAMES and category != budget.TIERED_SECTION  # investments already has a column
    head = "<th>Month</th><th>Earned</th><th>Spent</th><th>Invested</th><th>Saved</th>" + (f"<th>{SECTION_NAMES[category]}</th>" if extra else "")
    body = "".join(
        f"<tr><td>{row['label']} {row['key'][:4]}</td><td>{budget.format_money(row['income'])}</td>"
        f"<td>{budget.format_money(row['spent'])}</td><td>{budget.format_money(row['invested'])}</td>"
        f"<td>{budget.format_money(row['left'])}</td>"
        + (f"<td>{budget.format_money(row['sections'][category])}</td>" if extra else "")
        + "</tr>"
        for row in reversed(rows)
    )
    return (
        '<details class="sb-details"><summary>See the numbers</summary>'
        f'<div class="sb-table-wrap"><table class="sb-table"><tr>{head}</tr>{body}</table></div></details>'
    )


def top_items_html(items, category):
    """The biggest lines in the chosen category: the zoomed-in detail."""
    name = "investments" if category == budget.TIERED_SECTION else f"{SECTION_NAMES[category].lower()} items"
    title = f'<div class="sb-title">Biggest {name}</div>'
    if not items:
        return title + '<div class="sb-note" style="margin-top:6px">Nothing in this range yet.</div>'
    rows = "".join(
        f'<div class="sb-item-row"><span class="sb-line-name">{escape(name)}</span>'
        f'<span class="sb-note">{budget.month_name(key)[:3]} {key[:4]}</span>{design.money(cents)}</div>'
        for name, key, cents in items
    )
    return f'{title}<div class="sb-top-items">{rows}</div>'
