"""History charts for Sliced Bread: earned vs money out by month, zooming into a category, then a subcategory.
HTML only, no Gradio.

Built from plain HTML and CSS columns (not SVG) so labels stay readable at phone width. Follows the dataviz
rules: columns at most 24px wide with 4px rounded tops, 2px gaps between stacked pieces, hairline gridlines,
a legend, one callout above the plot, one hover/keyboard card per month, and a table with every number.
"""

from html import escape

import budget
import design

NICE_STEPS = (1, 2, 2.5, 5)  # tick steps, times a power of ten
TARGET_TICKS = 4  # gridlines above zero
HEADROOM = 1.12  # space above the tallest column for its label
COMPACT_FROM_CENTS = 10_000 * budget.CENTS_PER_DOLLAR  # axis switches to "$10K" style from here
# Month labels: show every Nth, counted back from the latest month, so they never run together.
LABEL_EVERY = ((12, 1), (24, 2))  # desktop: up to 12 months label all, up to 24 every other
PHONE_LABEL_EVERY = ((6, 1), (12, 2), (24, 4))  # phone widths fit about six labels
MAX_SHADED_ITEMS = 5  # lines named in a zoomed chart; smaller ones share one Other piece
OTHER_LABEL = "Other"
ALL_CHOICE = budget.ALL_SPENDING  # the zoom radio's label for the unzoomed chart
LEFT_OVER_LABEL = "Left over"  # what the Savings zoom adds on top of its subcategories
TOP_ITEMS = 5  # biggest lines listed under a zoomed chart


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


# ---------- What a zoom level shows ----------

def zoom_choices(user_budget):
    """The hidden zoom radio's (label, value) choices. Clicking a piece picks the choice whose label it names."""
    return (
        [(ALL_CHOICE, "all")]
        + [(budget.CATEGORY_NAMES[category], f"category:{category}") for category in budget.CATEGORIES]
        + [(sub["name"], f"sub:{sub['key']}") for sub in budget.subcategories(user_budget)]
    )


def zoom_series(lines, color):
    """The zoomed subcategory's lines ranked by their range total, biggest first, as [(label, color)]; the tail is Other."""
    totals = {}
    for month_lines in lines.values():
        for label, cents in month_lines.items():
            totals[label] = totals.get(label, 0) + cents
    ranked = sorted(totals, key=lambda label: totals[label], reverse=True)
    names = ranked[:MAX_SHADED_ITEMS] + ([OTHER_LABEL] if len(ranked) > MAX_SHADED_ITEMS else [])
    return list(zip(names, design.shades(color, len(names), design.DARKEST_MIX, design.ITEM_LIGHTEST_MIX))) if names else []


def month_amounts(month_lines, series):
    """One month's cents per series entry; lines outside the named ones add up into Other."""
    named = {label for label, _ in series if label != OTHER_LABEL}
    other = sum(cents for label, cents in month_lines.items() if label not in named)
    return [other if label == OTHER_LABEL else month_lines.get(label, 0) for label, _ in series]


def chart_view(user_budget, rows, pick):
    """What the chart shows for a zoom pick ("all", "category:needs", "sub:travel").

    series is [(name, color, zoom_to, [cents per row])], stacked bottom first. zoom_to names the choice a click opens.
    """
    kind, _, key = pick.partition(":")
    if kind == "category":
        colors = design.subcategory_colors(user_budget)
        subs = budget.subcategories_in(user_budget, key)
        series = [(sub["name"], colors[sub["key"]], sub["name"], [row["subcategories"][sub["key"]] for row in rows]) for sub in subs]
        if key == "savings":
            lightest = design.shades(design.CATEGORY_COLORS[key], 2, 0, design.LIGHTEST_MIX)[-1]
            series.append((LEFT_OVER_LABEL, lightest, None, [max(row["left"], 0) for row in rows]))
        return {"level": "category", "category": key, "name": budget.CATEGORY_NAMES[key], "series": series,
                "back": ALL_CHOICE, "sections": [sub["key"] for sub in subs]}
    if kind == "sub":
        sub = next(sub for sub in budget.subcategories(user_budget) if sub["key"] == key)
        lines = budget.section_lines(user_budget, [row["key"] for row in rows], key)
        shaded = zoom_series(lines, design.subcategory_colors(user_budget)[key])
        per_row = [month_amounts(lines[row["key"]], shaded) for row in rows]
        series = [(label, color, None, [amounts[index] for amounts in per_row]) for index, (label, color) in enumerate(shaded)]
        return {"level": "sub", "category": sub["category"], "name": sub["name"], "series": series,
                "back": budget.CATEGORY_NAMES[sub["category"]], "sections": [key]}
    series = [
        (budget.CATEGORY_NAMES[category], design.CATEGORY_COLORS[category], budget.CATEGORY_NAMES[category],
         [row["categories"][category] for row in rows])
        for category in budget.CATEGORIES
    ]
    return {"level": "all", "category": None, "name": ALL_CHOICE, "series": series, "back": None, "sections": []}


def view_totals(view, rows):
    """Each month's stacked total for a view."""
    return [sum(values[index] for _, _, _, values in view["series"]) for index in range(len(rows))]


# ---------- The chart ----------

def piece(value, color, zoom_to, is_top):
    """One stacked piece. The month's tooltip carries the numbers; a piece can zoom the chart to what it shows."""
    classes = "sb-seg" + (" sb-seg-top" if is_top else "") + (" sb-zoomable" if zoom_to else "")
    zoom = f' data-sb-zoom="{escape(zoom_to)}"' if zoom_to else ""
    return f'<div class="{classes}" style="flex:{value};background:{color}"{zoom}></div>'


def column(pieces, height_percent):
    """A column of stacked (value, color, zoom_to) pieces, bottom piece first, as tall as height_percent of the plot."""
    shown = [p for p in pieces if p[0] > 0]
    if not shown:
        return ""
    inner = "".join(piece(value, color, zoom_to, index == len(shown) - 1) for index, (value, color, zoom_to) in enumerate(shown))
    return f'<div class="sb-stack" style="height:{height_percent:.2f}%">{inner}</div>'


def tooltip(month, entries, total, opens_left):
    """The month's hover card: a swatch, name and amount per (name, color, cents), then the (name, cents) total."""
    rows = "".join(
        f'<div class="sb-tip-row"><i style="background:{color}"></i><span>{escape(name)}</span><b>{budget.format_money(cents)}</b></div>'
        for name, color, cents in entries
    )
    total_row = f'<div class="sb-tip-row sb-tip-total"><i></i><span>{total[0]}</span><b>{budget.format_money(total[1])}</b></div>'
    side = " sb-tip-left" if opens_left else ""
    return f'<div class="sb-tip{side}" aria-hidden="true"><div class="sb-tip-month">{month}</div>{rows}{total_row}</div>'


def month_column(month, stacks, entries, total, opens_left):
    """One month: its stacked columns plus the tooltip, focusable so the keyboard gets the same card."""
    summary = ", ".join(f"{name} {budget.format_money(cents)}" for name, _, cents in entries)
    label = escape(f"{month}: {summary}, {total[0]} {budget.format_money(total[1])}")
    return f'<div class="sb-month-col" tabindex="0" aria-label="{label}">{"".join(stacks)}{tooltip(month, entries, total, opens_left)}</div>'


def history_chart(rows, view):
    """Earned vs money out per month, or one category or subcategory split into its parts, bottom piece first."""
    zoomed = view["level"] != "all"
    totals = view_totals(view, rows)
    tallest = max(totals) if zoomed else max(max(row["income"], total) for row, total in zip(rows, totals))
    top, step = nice_ceiling(tallest)

    count = len(rows)
    columns = []
    for index, (row, total) in enumerate(zip(rows, totals)):
        pieces = [(values[index], color, zoom_to) for _, color, zoom_to, values in view["series"]]
        entries = [(name, color, values[index]) for name, color, _, values in view["series"] if values[index]]
        stacks = [column(pieces, total / top * 100)]
        if not zoomed:
            stacks.insert(0, column([(row["income"], design.INCOME_COLOR, None)], row["income"] / top * 100))
            entries.insert(0, ("Earned", design.INCOME_COLOR, row["income"]))
        total_label = "Total" if zoomed else "Money out"
        columns.append(month_column(full_month(row["key"]), stacks, entries, (total_label, total), index >= count / 2))

    grid = "".join(
        f'<div class="sb-grid" style="bottom:{value / top * 100:.2f}%"><span>{tick_label(value)}</span></div>'
        for value in range(0, top + 1, step)
    )
    every = next(step for limit, step in LABEL_EVERY if count <= limit)
    phone_every = next(step for limit, step in PHONE_LABEL_EVERY if count <= limit)
    months = "".join(
        f'<span class="{label_classes(count - 1 - index, every, phone_every)}">{row["label"]}</span>'
        for index, row in enumerate(rows)
    )
    title = f"{view['name']} by month" if zoomed else "Earned vs money out"
    # A zoomed subcategory carries its category's marker; a category is its own marker.
    marker = design.marker(view["category"]) if view["level"] == "sub" else ""
    span = full_month(rows[0]["key"]) if count == 1 else f"{full_month(rows[0]['key'])} to {full_month(rows[-1]['key'])}"
    back = f'<button class="sb-back" data-sb-zoom="{escape(view["back"])}">&larr; {escape(view["back"])}</button>' if zoomed else ""
    can_zoom = any(zoom_to for _, _, zoom_to, _ in view["series"])
    hint = '<div class="sb-note">Click a colour to see what it is made of.</div>' if can_zoom else ""
    return (
        f'<div class="sb-title">{escape(title)}{marker}</div><div class="sb-note">{span}</div>{back}{best_month_html(rows, view)}'
        f'<div class="sb-chart" role="group" aria-label="{escape(title)}, {escape(span)}">'
        f'<div class="sb-plot">{grid}<div class="sb-cols" style="grid-template-columns:repeat({count},minmax(0,1fr))">{"".join(columns)}</div></div>'
        f'<div class="sb-xaxis" style="grid-template-columns:repeat({count},minmax(0,1fr))">{months}</div></div>'
        f"{legend_html(view)}{hint}{numbers_table_html(rows, view)}"
    )


def best_month_html(rows, view):
    """The one callout: the month that stands out, above the chart so it never sits on a column."""
    if view["level"] != "all":
        amount, best = max(zip(view_totals(view, rows), rows), key=lambda pair: pair[0])
        text = f"Biggest month: {full_month(best['key'])}, {budget.format_money(amount)}"
    else:
        best = max(rows, key=lambda row: row["saved"])
        amount = best["saved"] if best["income"] else 0
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


def legend_html(view):
    """Every piece's colour and name; the ones that zoom in are buttons."""
    items = "" if view["level"] != "all" else f'<span><i style="background:{design.INCOME_COLOR}"></i>Earned</span>'
    for name, color, zoom_to, _ in view["series"]:
        swatch = f'<i style="background:{color}"></i>{escape(name)}'
        items += f'<button data-sb-zoom="{escape(zoom_to)}">{swatch}</button>' if zoom_to else f"<span>{swatch}</span>"
    return f'<div class="sb-legend">{items}</div>'


# ---------- Tiles, table and biggest items ----------

def stat_tiles_html(rows, view):
    """The range in numbers. Plain sans, proportional digits: these are standalone figures."""
    earned = sum(row["income"] for row in rows)
    if view["level"] != "all":
        total = sum(view_totals(view, rows))
        active = [row for row in rows if row["income"] or row["spent"] or row["invested"]] or rows
        share = f"{round(total * 100 / earned)}%" if earned else "0%"
        first = {"investing": "Invested", "savings": "Saved"}.get(view["category"], f"Spent on {view['name'].lower()}")
        tiles = [(first, budget.format_money(total), ""),
                 ("Monthly average", budget.format_money(total // len(active)), ""),
                 ("Share of income", share, "")]
    else:
        saved = sum(row["saved"] for row in rows)
        tiles = [("Earned", budget.format_money(earned), ""),
                 ("Spent", budget.format_money(sum(row["spent"] for row in rows)), ""),
                 ("Invested", budget.format_money(sum(row["invested"] for row in rows)), ""),
                 ("Saved", budget.format_money(saved), " sb-over" if saved < 0 else "")]
    cells = "".join(
        f'<div class="sb-tile"><div class="sb-eyebrow">{escape(label)}</div><div class="sb-tile-value{extra}">{value}</div></div>'
        for label, value, extra in tiles
    )
    return f'<div class="sb-tiles sb-tiles-{len(tiles)}">{cells}</div>'


def numbers_table_html(rows, view):
    """Every number in the chart, as a table: the version that needs no hovering."""
    if view["level"] == "all":
        columns = [("Earned", [row["income"] for row in rows]), ("Spent", [row["spent"] for row in rows]),
                   ("Invested", [row["invested"] for row in rows]), ("Saved", [row["saved"] for row in rows])]
    else:
        columns = [(name, values) for name, _, _, values in view["series"]] + [("Total", view_totals(view, rows))]
    head = "<th>Month</th>" + "".join(f"<th>{escape(name)}</th>" for name, _ in columns)
    body = "".join(
        f"<tr><td>{rows[index]['label']} {rows[index]['key'][:4]}</td>"
        + "".join(f"<td>{budget.format_money(values[index])}</td>" for _, values in columns)
        + "</tr>"
        for index in reversed(range(len(rows)))
    )
    return (
        '<details class="sb-details"><summary>See the numbers</summary>'
        f'<div class="sb-table-wrap"><table class="sb-table"><tr>{head}</tr>{body}</table></div></details>'
    )


def top_items(user_budget, rows, view):
    """The biggest lines across a zoomed view's subcategories: (name, month_key, cents), largest first."""
    keys = [row["key"] for row in rows]
    items = [item for section in view["sections"] for item in budget.top_items(user_budget, keys, section, TOP_ITEMS)]
    return sorted(items, key=lambda item: item[2], reverse=True)[:TOP_ITEMS]


def top_items_html(items, view):
    """The biggest lines in the zoomed view: the detail under the chart."""
    title = f'<div class="sb-title">Biggest in {escape(view["name"].lower())}</div>'
    if not items:
        return title + '<div class="sb-note" style="margin-top:6px">Nothing in this range yet.</div>'
    rows = "".join(
        f'<div class="sb-item-row"><span class="sb-line-name">{escape(name)}</span>'
        f'<span class="sb-note">{budget.month_name(key)[:3]} {key[:4]}</span>{design.money(cents)}</div>'
        for name, key, cents in items
    )
    return f'{title}<div class="sb-top-items">{rows}</div>'
