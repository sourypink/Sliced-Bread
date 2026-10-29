"""Budget math for Sliced Bread: pure functions, no Gradio, all money in whole cents."""

from datetime import date

# The page reads top to bottom in this order; investments are computed, never stored.
SECTIONS = ("income", "necessities", "discretionary", "travel")
EXPENSE_SECTIONS = ("necessities", "discretionary", "travel")
LIMIT_KEYS = ("overall",) + EXPENSE_SECTIONS

# Percentage targets: which sections count as needs and wants. Savings is whatever is left.
TARGET_KEYS = ("needs", "wants", "savings")
TARGET_GROUPS = {"needs": ("necessities",), "wants": ("discretionary", "travel")}
RULE_50_30_20 = {"needs": 50, "wants": 30, "savings": 20}
PERCENT_WHOLE = 100

WARN_AT = 0.9  # share of a limit at which the meter turns to "near limit"
MAX_AMOUNT_CENTS = 10_000_000 * 100  # $10M; anything larger is a typo
MAX_NAME_LENGTH = 40  # characters
CENTS_PER_DOLLAR = 100


def empty_month():
    """A month with every section present and empty."""
    return {section: [] for section in SECTIONS}


def empty_budget():
    """A new user's budget: no limits, no goal, no months."""
    return {
        "settings": {"savings_goal": 0, "limits": {key: 0 for key in LIMIT_KEYS}, "targets": {}},
        "months": {},
    }


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


def parse_optional_amount(text):
    """Like parse_amount, but blank or 0 means "not set" and returns 0."""
    cleaned = str(text if text is not None else "").strip().replace("$", "").replace(",", "")
    if cleaned.strip("0.") == "":
        return 0
    return parse_amount(cleaned)


def clean_name(text):
    """Trim a line item's name, or raise ValueError if it is unusable."""
    name = " ".join(str(text if text is not None else "").split())
    if not name:
        raise ValueError("Enter a name")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name must be {MAX_NAME_LENGTH} characters or fewer")
    return name


def format_money(cents):
    """$1,200 for whole dollars, $12.50 otherwise, -$85 when negative."""
    sign = "-" if cents < 0 else ""
    dollars, remainder = divmod(abs(cents), CENTS_PER_DOLLAR)
    if remainder:
        return f"{sign}${dollars:,}.{remainder:02d}"
    return f"{sign}${dollars:,}"


def section_total(month, section):
    """Sum of every line in one section."""
    return sum(item["amount"] for item in month.get(section, []))


def total_expenses(month):
    """Necessities + discretionary + travel."""
    return sum(section_total(month, section) for section in EXPENSE_SECTIONS)


def leftover(month):
    """Income minus expenses: what goes to investments. Negative means over budget."""
    return section_total(month, "income") - total_expenses(month)


def meter(spent, limit):
    """State of a spending limit: none (no limit set), good, warn or over, with its label."""
    if limit <= 0:
        return {"state": "none", "fraction": 0.0, "label": ""}
    fraction = spent / limit
    if spent > limit:
        return {"state": "over", "fraction": 1.0, "label": f"Over by {format_money(spent - limit)}"}
    if fraction >= WARN_AT:
        return {"state": "warn", "fraction": fraction, "label": f"Near limit, {format_money(limit - spent)} left"}
    return {"state": "good", "fraction": fraction, "label": f"{format_money(limit - spent)} left"}


def savings_progress(budget):
    """Saved so far: the positive leftovers of every month added up."""
    return sum(max(0, leftover(month)) for month in budget["months"].values())


def add_item(budget, month_key, section, name_text, amount_text):
    """Validate and add a line to a section; returns the added item."""
    if section not in SECTIONS:
        raise ValueError(f"Unknown section: {section}")
    item = {"name": clean_name(name_text), "amount": parse_amount(amount_text)}
    month = budget["months"].setdefault(month_key, empty_month())
    month[section].append(item)
    return item


def remove_item(budget, month_key, section, index):
    """Delete one line from a section by its position."""
    items = budget["months"].get(month_key, empty_month())[section]
    if not 0 <= index < len(items):
        raise IndexError(f"No line {index} in {section}")
    items.pop(index)


def update_item(budget, month_key, section, index, name_text, amount_text):
    """Validate and replace one line; returns the new item."""
    items = budget["months"].get(month_key, empty_month())[section]
    if not 0 <= index < len(items):
        raise IndexError(f"No line {index} in {section}")
    item = {"name": clean_name(name_text), "amount": parse_amount(amount_text)}
    items[index] = item
    return item


def parse_targets(needs_text, wants_text, savings_text):
    """Turn three typed percentages into targets. All blank means targets are off ({})."""
    typed = dict(zip(TARGET_KEYS, (needs_text, wants_text, savings_text)))
    cleaned = {key: str(text if text is not None else "").strip().rstrip("%").strip() for key, text in typed.items()}
    if not any(cleaned.values()):
        return {}
    targets = {}
    for key, text in cleaned.items():
        if not text.isdigit() or int(text) > PERCENT_WHOLE:
            raise ValueError(f"{key.capitalize()} must be a whole number from 0 to 100")
        targets[key] = int(text)
    total = sum(targets.values())
    if total != PERCENT_WHOLE:
        raise ValueError(f"Targets must add up to 100% (now {total}%)")
    return targets


def target_meters(targets, month):
    """Each target's meter, with the actual and target percent of income. Empty when off or no income."""
    income = section_total(month, "income")
    if not targets or income <= 0:
        return {}
    meters = {}
    for key, sections in TARGET_GROUPS.items():
        spent = sum(section_total(month, section) for section in sections)
        result = meter(spent, income * targets[key] // PERCENT_WHOLE)
        meters[key] = {**result, "actual_percent": round(spent * PERCENT_WHOLE / income), "target_percent": targets[key]}
    saved = max(leftover(month), 0)
    goal = income * targets["savings"] // PERCENT_WHOLE
    if goal <= 0:
        result = {"state": "none", "fraction": 0.0, "label": ""}
    elif saved >= goal:
        result = {"state": "good", "fraction": 1.0, "label": "On target"}
    else:
        result = {"state": "warn", "fraction": saved / goal, "label": f"{format_money(goal - saved)} short"}
    meters["savings"] = {**result, "actual_percent": round(saved * PERCENT_WHOLE / income), "target_percent": targets["savings"]}
    return meters


def get_month(budget, month_key):
    """The month's data, or an empty month if nothing was entered yet."""
    return budget["months"].get(month_key, empty_month())


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
