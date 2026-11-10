"""Budget math for Sliced Bread: pure functions, no Gradio, all money in whole cents."""

import re
from datetime import date

# Money comes in as income and goes out into subcategories (Rent goes in Necessities). Every subcategory sits in
# one of four fixed categories, which the percentage targets and History are built on.
INCOME = "income"
CATEGORIES = ("needs", "wants", "investing", "savings")
CATEGORY_NAMES = {"needs": "Needs", "wants": "Wants", "investing": "Investing", "savings": "Savings"}
SPENDING_CATEGORIES = ("needs", "wants")  # targets to stay under, and what "spent" covers; investing and savings are minimums
PRESET_SUBCATEGORIES = (
    {"key": "necessities", "name": "Necessities", "category": "needs"},
    {"key": "discretionary", "name": "Discretionary", "category": "wants"},
    {"key": "investments", "name": "Investments", "category": "investing"},
)
PRESET_KEYS = tuple(preset["key"] for preset in PRESET_SUBCATEGORIES)
# Former presets: kept in budgets that hold lines under them but never saved their list, so no money goes missing.
RETIRED_PRESETS = (
    {"key": "travel", "name": "Travel", "category": "wants"},
    {"key": "emergency_fund", "name": "Emergency fund", "category": "savings"},
)
MAX_CUSTOM_SUBCATEGORIES = 8
ALL_SPENDING = "All spending"  # History's unzoomed view
UNSAFE_KEY_CHARACTERS = re.compile(r"[^a-z0-9]+")

# Starting plans the user can pick at sign-up or from Goals, each with the research behind it.
PLAN_PRESETS = (
    {
        "key": "balanced", "name": "Balanced",
        "targets": {"needs": 50, "wants": 30, "investing": 15, "savings": 5},
        "why": "Half on must-haves, 15% for retirement, 5% for short-term savings.",
        "source": "Warren & Tyagi, All Your Worth (2005): 50/30/20. Fidelity's 50/15/5 saving guideline.",
    },
    {
        "key": "safety_net", "name": "Safety net first",
        "targets": {"needs": 50, "wants": 20, "investing": 10, "savings": 20},
        "why": "Build an emergency fund before investing hard.",
        "source": "Vanguard (2025, 12,400 investors): $2,000+ in emergency savings, 21% higher financial well-being.",
    },
    {
        "key": "invest_more", "name": "Invest more",
        "targets": {"needs": 45, "wants": 20, "investing": 30, "savings": 5},
        "why": "A higher saving rate reaches retirement sooner.",
        "source": "Fidelity: save more than 15% to retire before 67. Bengen (1994), the 4% rule: aim for 25x yearly spending.",
    },
)
PERCENT_WHOLE = 100

WARN_AT = 0.9  # share of a target at which its meter turns to "near limit"
MAX_AMOUNT_CENTS = 10_000_000 * 100  # $10M; anything larger is a typo
MAX_NAME_LENGTH = 40  # characters
CENTS_PER_DOLLAR = 100


def empty_budget():
    """A new user's budget: no targets, no months."""
    return {"settings": {"targets": {}}, "months": {}}


# ---------- Checking what the user typed ----------

def parse_amount(text):
    """Turn what the user typed into cents, or raise ValueError saying what is wrong."""
    cleaned = str(text if text is not None else "").strip().replace("$", "").replace(",", "")
    if not cleaned:
        raise ValueError("Enter an amount")
    if cleaned.startswith("-"):
        raise ValueError("Amount can't be negative")
    whole, _, fraction = cleaned.partition(".")
    if not (whole or fraction) or not (whole or "0").isdigit() or (fraction and not fraction.isdigit()):
        raise ValueError("Amount must be a number, like 12.50")
    if len(fraction) > 2:
        raise ValueError("Amount can have at most 2 decimal places")
    cents = int(whole or 0) * CENTS_PER_DOLLAR + int(fraction.ljust(2, "0"))
    if cents == 0:
        raise ValueError("Amount must be more than $0")
    if cents > MAX_AMOUNT_CENTS:
        raise ValueError("Amount is too large")
    return cents


def clean_name(text):
    """Trim a line item's name, or raise ValueError if it is unusable."""
    name = " ".join(str(text if text is not None else "").split())
    if not name:
        raise ValueError("Enter a name")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name must be {MAX_NAME_LENGTH} characters or fewer")
    return name


def make_item(name_text, amount_text):
    """A validated line."""
    return {"name": clean_name(name_text), "amount": parse_amount(amount_text)}


def format_money(cents):
    """$1,200 for whole dollars, $12.50 otherwise, -$85 when negative."""
    sign = "-" if cents < 0 else ""
    dollars, remainder = divmod(abs(cents), CENTS_PER_DOLLAR)
    if remainder:
        return f"{sign}${dollars:,}.{remainder:02d}"
    return f"{sign}${dollars:,}"


# ---------- Subcategories ----------

def missing_presets(budget, subs):
    """Presets a saved list lacks (saved before subcategories, or before a preset was added), unless removed."""
    keys = {sub["key"] for sub in subs} | set(budget["settings"].get("removed_presets", []))
    used = {section for month in budget["months"].values() for section, items in month.items() if items}
    retired = [preset for preset in RETIRED_PRESETS if preset["key"] in used]
    return [dict(preset) for preset in PRESET_SUBCATEGORIES + tuple(retired) if preset["key"] not in keys]


def subcategories(budget):
    """Every subcategory in page order within its category."""
    stored = budget["settings"].get("subcategories", [])
    return stored + missing_presets(budget, stored)


def editable_subcategories(budget):
    """The stored list to change, with any missing presets written in."""
    subs = budget["settings"].setdefault("subcategories", [])
    subs.extend(missing_presets(budget, subs))
    return subs


def subcategories_in(budget, category):
    return [sub for sub in subcategories(budget) if sub["category"] == category]


def section_keys(budget):
    """Income first, then every subcategory key: what a month holds lines under."""
    return [INCOME] + [sub["key"] for sub in subcategories(budget)]


def find_subcategory(budget, key):
    for sub in editable_subcategories(budget):
        if sub["key"] == key:
            return sub
    raise ValueError(f"Unknown subcategory: {key}")


def check_category(category):
    if category not in CATEGORIES:
        raise ValueError("Pick a category: Needs, Wants, Investing or Savings")


def unused_name(budget, name_text, except_key=None):
    """A cleaned subcategory name nobody else has, ignoring capitals."""
    name = clean_name(name_text)
    # History zooms by clicking a name, so a subcategory can't share one with a category or the unzoomed view.
    reserved = {INCOME, ALL_SPENDING.lower()} | {category_name.lower() for category_name in CATEGORY_NAMES.values()}
    taken = {sub["name"].lower() for sub in subcategories(budget) if sub["key"] != except_key} | reserved
    if name.lower() in taken:
        raise ValueError(f"You already have {name}")
    return name


def add_subcategory(budget, name_text, category):
    """A new subcategory of the user's own, at the end of its category; returns it."""
    check_category(category)
    name = unused_name(budget, name_text)
    subs = editable_subcategories(budget)
    if sum(sub["key"] not in PRESET_KEYS for sub in subs) >= MAX_CUSTOM_SUBCATEGORIES:
        raise ValueError(f"You can add up to {MAX_CUSTOM_SUBCATEGORIES} of your own subcategories")
    # The key is fixed for good, so a rename never detaches past months' lines.
    base = UNSAFE_KEY_CHARACTERS.sub("_", name.lower()).strip("_") or "subcategory"
    taken = set(section_keys(budget))
    key, number = base, 2
    while key in taken:
        key, number = f"{base}_{number}", number + 1
    sub = {"key": key, "name": name, "category": category}
    subs.append(sub)
    return sub


def rename_subcategory(budget, key, name_text):
    find_subcategory(budget, key)["name"] = unused_name(budget, name_text, except_key=key)


def move_subcategory(budget, key, category):
    """Put a subcategory under another category. It goes to the end of that category's list."""
    check_category(category)
    subs = editable_subcategories(budget)
    sub = find_subcategory(budget, key)
    if sub["category"] != category:
        subs.remove(sub)
        subs.append({**sub, "category": category})


def remove_subcategory(budget, key):
    """Delete a subcategory, preset or not. Refused while any month has lines in it, so nothing is lost."""
    sub = find_subcategory(budget, key)
    used = sum(1 for month in budget["months"].values() if month.get(key))
    if used:
        plural = "s" if used > 1 else ""
        raise ValueError(f"{sub['name']} has items in {used} month{plural}. Delete them first.")
    editable_subcategories(budget).remove(sub)
    if key in PRESET_KEYS:  # so it isn't added back as "missing"
        budget["settings"].setdefault("removed_presets", []).append(key)
    for month in budget["months"].values():
        month.pop(key, None)


# ---------- Totals ----------

def section_total(month, section):
    """Sum of every line in one section."""
    return sum(item["amount"] for item in month.get(section, []))


def category_total(budget, month, category):
    """Sum of every subcategory in one category."""
    return sum(section_total(month, sub["key"]) for sub in subcategories_in(budget, category))


def total_expenses(budget, month):
    """Needs + wants: what "spent" covers."""
    return sum(category_total(budget, month, category) for category in SPENDING_CATEGORIES)


def total_invested(budget, month):
    """Everything put into investing subcategories this month."""
    return category_total(budget, month, "investing")


def total_set_aside(budget, month):
    """Money moved into savings subcategories on purpose, like an emergency fund."""
    return category_total(budget, month, "savings")


def leftover(budget, month):
    """Income minus everything that went out. Negative means over budget."""
    return section_total(month, INCOME) - sum(category_total(budget, month, category) for category in CATEGORIES)


def saved(budget, month):
    """Set aside plus whatever is left over (never below the set-aside)."""
    return total_set_aside(budget, month) + max(leftover(budget, month), 0)


def meter(spent, target):
    """State of a target to stay under: none (not set), good, warn or over, with its label."""
    if target <= 0:
        return {"state": "none", "fraction": 0.0, "label": ""}
    fraction = spent / target
    if spent > target:
        return {"state": "over", "fraction": 1.0, "label": f"Over by {format_money(spent - target)}"}
    if fraction >= WARN_AT:
        return {"state": "warn", "fraction": fraction, "label": f"Near target, {format_money(target - spent)} left"}
    return {"state": "good", "fraction": fraction, "label": f"{format_money(target - spent)} left"}


# ---------- Lines ----------

def editable_month(budget, month_key):
    """The stored month to change, created if new, with every section present (older saves lack some)."""
    month = budget["months"].setdefault(month_key, {})
    for section in section_keys(budget):
        month.setdefault(section, [])
    return month


def add_item(budget, month_key, section, name_text, amount_text):
    """Validate and add a line to a section; returns the added item."""
    if section not in section_keys(budget):
        raise ValueError(f"Unknown section: {section}")
    item = make_item(name_text, amount_text)
    editable_month(budget, month_key)[section].append(item)
    return item


def remove_item(budget, month_key, section, index):
    """Delete one line from a section by its position."""
    items = editable_month(budget, month_key)[section]
    if not 0 <= index < len(items):
        raise IndexError(f"No line {index} in {section}")
    items.pop(index)


def update_item(budget, month_key, section, index, name_text, amount_text):
    """Validate and replace one line; returns the new item."""
    items = editable_month(budget, month_key)[section]
    if not 0 <= index < len(items):
        raise IndexError(f"No line {index} in {section}")
    item = make_item(name_text, amount_text)
    items[index] = item
    return item


# ---------- Percentage targets ----------

def target_number(text):
    """A typed percentage as a whole number from 0 to 100, or None if it isn't one."""
    cleaned = str(text if text is not None else "").strip().rstrip("%").strip()
    return int(cleaned) if cleaned.isdigit() and int(cleaned) <= PERCENT_WHOLE else None


def is_blank(text):
    return not str(text if text is not None else "").strip()


def parse_targets(needs_text, wants_text, investing_text, savings_text):
    """Turn four typed percentages into targets. All blank means targets are off ({})."""
    typed = dict(zip(CATEGORIES, (needs_text, wants_text, investing_text, savings_text)))
    if all(is_blank(text) for text in typed.values()):
        return {}
    targets = {}
    for key, text in typed.items():
        targets[key] = target_number(text)
        if targets[key] is None:
            raise ValueError(f"{CATEGORY_NAMES[key]} must be a whole number from 0 to 100")
    total = sum(targets.values())
    if total != PERCENT_WHOLE:
        raise ValueError(f"Your split must add up to 100% (now {total}%)")
    return targets


def complete_targets(texts, auto_key, edited_key):
    """Fill the one blank target box with what makes 100, and keep it in step while the other three change.

    Returns the four box texts and the box filled in for the user (None once they type in it themselves). The box
    that changed is never rewritten, so the caller only needs to update the other three.
    """
    values = dict(zip(CATEGORIES, texts))

    def remainder(key):
        others = [target_number(text) for other, text in values.items() if other != key]
        return str(PERCENT_WHOLE - sum(others)) if None not in others and sum(others) <= PERCENT_WHOLE else ""

    if edited_key == auto_key:
        # The filled-in box changed: either this function's own update, or the user typing over it.
        return list(texts), auto_key if values[auto_key] == remainder(auto_key) else None
    if auto_key is None:
        blanks = [key for key, text in values.items() if is_blank(text)]
        # Never fill the box being typed in: clearing a box means the user is about to type a new number there.
        if len(blanks) != 1 or edited_key in blanks or not remainder(blanks[0]):
            return list(texts), None
        auto_key = blanks[0]
    values[auto_key] = remainder(auto_key)
    return [values[key] for key in CATEGORIES], auto_key


def share_of(cents, percent):
    """percent of an amount, rounded down to the cent."""
    return cents * percent // PERCENT_WHOLE


def minimum_meter(reached, goal):
    """A target to reach rather than stay under: short is amber, reaching it is good."""
    if goal <= 0:
        return {"state": "none", "fraction": 0.0, "label": ""}
    if reached >= goal:
        return {"state": "good", "fraction": 1.0, "label": "On target"}
    return {"state": "warn", "fraction": reached / goal, "label": f"{format_money(goal - reached)} to go"}


def target_meters(budget, targets, month):
    """Each category's meter, with the actual and target percent of income. Empty when off or no income."""
    income = section_total(month, INCOME)
    # Targets saved before investing had its own share have three keys; they count as off.
    if set(targets) != set(CATEGORIES) or income <= 0:
        return {}
    reached = {category: category_total(budget, month, category) for category in CATEGORIES}
    reached["savings"] = saved(budget, month)
    meters = {}
    for category in CATEGORIES:
        goal = share_of(income, targets[category])
        check = meter if category in SPENDING_CATEGORIES else minimum_meter
        meters[category] = {
            **check(reached[category], goal),
            "actual_percent": round(reached[category] * PERCENT_WHOLE / income),
            "target_percent": targets[category],
        }
    return meters


# ---------- Months ----------

def get_month(budget, month_key):
    """The month's data with every section present, or an empty month if nothing was entered yet."""
    return {**{section: [] for section in section_keys(budget)}, **budget["months"].get(month_key, {})}


def month_key(day=None):
    """'2026-10' for any date in October 2026; today by default."""
    day = day or date.today()
    return f"{day.year}-{day.month:02d}"


def shift_month(key, steps):
    """Move a month key forward or back: shift_month('2026-12', 1) is '2027-01'."""
    year, month = (int(part) for part in key.split("-"))
    index = year * 12 + (month - 1) + steps
    return f"{index // 12}-{index % 12 + 1:02d}"


def month_name(key):
    """'October' for '2026-10'."""
    year, month = (int(part) for part in key.split("-"))
    return date(year, month, 1).strftime("%B")


def month_label(key):
    """'October 2026' for '2026-10'."""
    return f"{month_name(key)} {key.split('-')[0]}"


# ---------- History ----------

HISTORY_RANGES = {"6 months": 6, "12 months": 12}  # "All" is the third choice, from the first month with data
MAX_HISTORY_MONTHS = 24  # columns stay readable up to two years
SAMPLE_TAG = " (sample)"

# Five believable earlier months for demos, oldest first: (section, name, dollars).
SAMPLE_ROTH = ("investments", "Roth IRA", 250)
SAMPLE_INDEX = ("investments", "Index fund", 150)
SAMPLE_MONTHS = [
    [("income", "Salary", 3000), ("necessities", "Rent", 1200), ("necessities", "Groceries", 340),
     ("necessities", "Gas", 110), ("discretionary", "Streaming", 28), ("discretionary", "Dinner out", 90),
     SAMPLE_ROTH],
    [("income", "Salary", 3000), ("income", "Freelance", 250), ("necessities", "Rent", 1200),
     ("necessities", "Groceries", 365), ("necessities", "Gas", 95), ("discretionary", "Concert tickets", 140),
     ("discretionary", "Streaming", 28), SAMPLE_ROTH, SAMPLE_INDEX],
    [("income", "Salary", 3000), ("necessities", "Rent", 1200), ("necessities", "Groceries", 410),
     ("necessities", "Gas", 120), ("discretionary", "Streaming", 28), ("discretionary", "Flights", 380),
     ("discretionary", "Hotel", 420), ("discretionary", "Food on the trip", 160), SAMPLE_ROTH],
    [("income", "Salary", 3000), ("income", "Freelance", 400), ("necessities", "Rent", 1200),
     ("necessities", "Groceries", 350), ("necessities", "Gas", 105), ("discretionary", "Video game", 70),
     ("discretionary", "Streaming", 28), SAMPLE_ROTH, SAMPLE_INDEX],
    [("income", "Salary", 3000), ("necessities", "Rent", 1200), ("necessities", "Groceries", 375),
     ("necessities", "Gas", 115), ("discretionary", "Movies", 45), ("discretionary", "Streaming", 28),
     ("discretionary", "Weekend train", 90), SAMPLE_ROTH, SAMPLE_INDEX],
]
def month_history(budget, end_key, count):
    """One row per month, oldest first, ending at end_key. Months with nothing entered are zeros."""
    rows = []
    for steps in range(count - 1, -1, -1):
        key = shift_month(end_key, -steps)
        month = get_month(budget, key)
        left = leftover(budget, month)
        rows.append({
            "key": key,
            "label": month_name(key)[:3],
            "income": section_total(month, INCOME),
            "spent": total_expenses(budget, month),
            "invested": total_invested(budget, month),
            "left": left,
            "saved": total_set_aside(budget, month) + left,  # negative when over budget
            "categories": {category: category_total(budget, month, category) for category in CATEGORIES},
            "subcategories": {sub["key"]: section_total(month, sub["key"]) for sub in subcategories(budget)},
        })
    return rows


def history_range(budget, choice, today_key):
    """The (end_key, count) a range choice covers. 'All' runs from the first month with data to today."""
    if choice in HISTORY_RANGES:
        return today_key, HISTORY_RANGES[choice]
    keys = [key for key, month in budget["months"].items() if any(month.values()) and key <= today_key]
    if not keys:
        return today_key, 1
    first = min(keys)
    first_year, first_month = (int(part) for part in first.split("-"))
    year, month = (int(part) for part in today_key.split("-"))
    span = (year - first_year) * 12 + (month - first_month) + 1
    return today_key, min(span, MAX_HISTORY_MONTHS)


def months_with_data(budget):
    """How many months have at least one line."""
    return sum(1 for month in budget["months"].values() if any(month.values()))


def top_items(budget, keys, section, limit=5):
    """The biggest lines in a section across the given months: (name, month_key, cents), largest first."""
    items = [(item["name"], key, item["amount"]) for key in keys for item in get_month(budget, key)[section]]
    return sorted(items, key=lambda item: item[2], reverse=True)[:limit]


def section_lines(budget, keys, section):
    """Each month's lines in one section as {month_key: {label: cents}}; lines sharing a label add up."""
    months = {}
    for key in keys:
        totals = months.setdefault(key, {})
        for item in get_month(budget, key)[section]:
            label = item["name"]
            totals[label] = totals.get(label, 0) + item["amount"]
    return months


def fill_sample_months(budget, current_key):
    """Fill the five months before current_key with sample lines, skipping any that already have data."""
    filled = 0
    for steps, lines in zip(range(len(SAMPLE_MONTHS), 0, -1), SAMPLE_MONTHS):
        key = shift_month(current_key, -steps)
        if any(get_month(budget, key).values()):
            continue
        for section, name, dollars in lines:
            if section not in section_keys(budget):  # a preset the user removed
                continue
            add_item(budget, key, section, name + SAMPLE_TAG, str(dollars))
        filled += 1
    return filled
