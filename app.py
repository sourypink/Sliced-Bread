"""Sliced Bread: a personal budget tracker. Run with: python app.py"""

import copy
import sys
from html import escape

import gradio as gr

import budget
import charts
import design
import storage

INCOME_NAME = "Income"
EMPTY_STATES = {
    "income": "No income yet. Add your salary, freelance or other pay.",
    "necessities": "Nothing yet. Add rent, groceries, gas.",
    "discretionary": "Nothing yet. Add movies, trips, games, subscriptions.",
    "investments": "Nothing yet. Add a Roth IRA, index fund or brokerage deposit.",
}
CUSTOM_EMPTY_STATE = "Nothing yet."
NAME_PLACEHOLDERS = {
    "income": "Salary", "necessities": "Rent", "discretionary": "Concert tickets", "investments": "Roth IRA",
}
MONTHLY_LIMIT = "Monthly limit"
CATEGORY_PICKER_WIDTH = 124  # px: fits "Investing" and the dropdown arrow
CATEGORY_OPTIONS = [(budget.CATEGORY_NAMES[category], category) for category in budget.CATEGORIES]
RANGE_CHOICES = ["6 months", "12 months", "All"]
SAMPLE_OFFER_BELOW = 3  # months with data; under this, History offers sample months


def html(value, **options):
    return gr.HTML(value, padding=False, **options)


def fail(message):
    """Show a validation problem to the user without a traceback in the console."""
    return gr.Error(message, print_exception=False)


def changed(user, user_budget, change, *args):
    """Apply one budget change to a copy, save it and return it; a ValueError becomes a message to the user."""
    updated = copy.deepcopy(user_budget)
    try:
        change(updated, *args)
    except ValueError as error:
        raise fail(str(error))
    storage.save_budget(user, updated)
    return updated


def sections(user_budget):
    """Every section on the Budget page as (key, name, category): income, then subcategories by category."""
    return [(budget.INCOME, INCOME_NAME, None)] + [
        (sub["key"], sub["name"], category)
        for category in budget.CATEGORIES
        for sub in budget.subcategories_in(user_budget, category)
    ]


def limit_meters(user_budget, month):
    """Each limit's (meter, words) by the name alerts give it: Needs and Wants as their share of the monthly limit,
    or the monthly limit on all spending while targets are off."""
    settings = user_budget["settings"]
    shares = budget.category_limits(settings)
    if shares:
        meters = {}
        for category in budget.SPENDING_CATEGORIES:
            name, spent = budget.CATEGORY_NAMES[category], budget.category_total(user_budget, month, category)
            words = f"{name} {budget.format_money(spent)} of {budget.format_money(shares[category])}"
            meters[f"{name} limit"] = (budget.meter(spent, shares[category]), words)
        return meters
    overall = settings["limits"].get("overall", 0)
    spent = budget.total_expenses(user_budget, month)
    return {MONTHLY_LIMIT: (budget.meter(spent, overall), f"Spent {budget.format_money(spent)} of {budget.format_money(overall)}")}


# ---------- Page pieces ----------

def month_title_html(key):
    return f'<div class="sb-month-label">{budget.month_label(key)}</div>'


def person_html(user_budget):
    return f'<span class="sb-person-name">{escape(user_budget["account"]["name"])}</span>' if user_budget else ""


def initial(user_budget):
    return user_budget["account"]["name"][:1].upper() if user_budget else ""


def duck_line(user_budget, key):
    """What the duck says under the hero: one line picked from the month's state. The mascot's only job for now."""
    month = budget.get_month(user_budget, key)
    if budget.section_total(month, budget.INCOME) == 0:
        return "Add your income and I'll do the math."
    left = budget.leftover(user_budget, month)
    if left < 0:
        return "Quack. More went out than came in this month."
    meters = watched_meters(user_budget, key)
    for label, result in meters.items():
        if result["state"] == "over":
            return f"Heads up: {label.lower()} is {result['label'].lower()}."
    for label, result in meters.items():
        if result["state"] == "warn":
            return f"Careful, {label.lower()} is near its limit."
    return f"Nice. {budget.format_money(budget.saved(user_budget, month))} saved this month."


def hero_html(user_budget, key):
    """The big number, where the money went by category, and the duck."""
    month = budget.get_month(user_budget, key)
    income = budget.section_total(month, budget.INCOME)
    left = budget.leftover(user_budget, month)

    if left >= 0:
        top = f'<div class="sb-eyebrow">Left to save</div><div class="sb-hero-amount">{budget.format_money(left)}</div>'
    else:
        top = f'<div class="sb-eyebrow">Over budget</div><div class="sb-hero-amount sb-over">{budget.format_money(-left)}</div>'

    amounts = {category: budget.category_total(user_budget, month, category) for category in budget.CATEGORIES}
    amounts["savings"] = budget.saved(user_budget, month)
    key_items = "".join(
        f"<span>{design.dot(design.CATEGORY_COLORS[category])}{budget.CATEGORY_NAMES[category]} {design.money(cents)}</span>"
        for category, cents in amounts.items() if cents
    )
    meters = "".join(design.meter_html(result, words, blend=True) for result, words in limit_meters(user_budget, month).values())
    duck = (
        f'<div class="sb-duck-says"><span class="sb-bob">{design.duck_mark(44)}</span>'
        f'<div class="sb-bubble">{escape(duck_line(user_budget, key))}</div></div>'
    )
    return (
        f'{top}<div class="sb-donut-row">{design.donut_svg(amounts, income)}<div class="sb-key">{key_items}</div></div>'
        + (f'<div class="sb-split">{meters}</div>' if meters else "")
        + duck
    )


def section_head_html(user_budget, month, section, name, category):
    """A section's title, the category it counts toward, and its total."""
    total = budget.section_total(month, section)
    color = design.INCOME_COLOR if category is None else design.subcategory_colors(user_budget)[section]
    marker = design.marker(category) if category else ""
    return (
        f'<div class="sb-head"><div class="sb-title">{design.dot(color)}<span class="sb-title-name">{escape(name)}</span>{marker}</div>'
        f'<div class="sb-head-total">{design.money(total)}</div></div>'
    )


def savings_html(user_budget, key):
    """The Savings category: what was set aside on purpose plus what is left over, and the savings goal."""
    month = budget.get_month(user_budget, key)
    left = budget.leftover(user_budget, month)
    set_aside = budget.total_set_aside(user_budget, month)
    head = f'<div class="sb-title">{design.dot(design.CATEGORY_COLORS["savings"])}Savings</div>'
    amount = f'<div class="sb-big" style="margin-top:12px">{budget.format_money(budget.saved(user_budget, month))}</div>'
    if left < 0:
        note = f'<div class="sb-note" style="color:var(--sb-over)">Over budget by {budget.format_money(-left)}. Nothing left over.</div>'
    elif set_aside:
        note = f'<div class="sb-note">{budget.format_money(set_aside)} set aside, {budget.format_money(left)} left over.</div>'
    else:
        note = '<div class="sb-note">Whatever is left after spending and investing lands here.</div>'
    goal = user_budget["settings"]["savings_goal"]
    if goal:
        progress = design.progress_html(budget.savings_progress(user_budget), goal)
    else:
        progress = '<div class="sb-note">Set a savings goal on the Goals tab.</div>'
    return f'{head}{amount}<div style="margin-top:6px">{note}</div><div style="margin-top:16px">{progress}</div>'


def split_html(user_budget, month):
    """Each category against the user's percentage targets, under the same marker as its sections. Empty when off."""
    targets = user_budget["settings"].get("targets", {})
    meters = budget.target_meters(user_budget, targets, month)
    if not meters:
        return ""
    plan = "/".join(str(targets[category]) for category in budget.CATEGORIES)
    rows = "".join(
        f'<div class="sb-split-row">{design.marker(category)}'
        f'{design.meter_html(result, f"{result["actual_percent"]}% of {result["target_percent"]}%", blend=category in budget.SPENDING_CATEGORIES)}</div>'
        for category, result in meters.items()
    )
    return f'<div class="sb-title">Your {plan} split</div><div class="sb-split">{rows}</div>'


def watched_meters(user_budget, key):
    """Every limit and target an alert watches, by the name the alert shows."""
    month = budget.get_month(user_budget, key)
    meters = {label: result for label, (result, _) in limit_meters(user_budget, month).items()}
    targets = budget.target_meters(user_budget, user_budget["settings"].get("targets", {}), month)
    # Only needs and wants are limits; investing and savings are minimums, so they never alert.
    meters.update({
        f"{budget.CATEGORY_NAMES[category]} target": result
        for category, result in targets.items() if category in budget.SPENDING_CATEGORIES
    })
    return meters


def budget_alerts(before, after, key):
    """Warn when a change pushes a limit or target into "near" or "over"."""
    old = watched_meters(before, key)
    for label, new in watched_meters(after, key).items():
        if new["state"] in ("warn", "over") and new["state"] != old.get(label, {"state": "none"})["state"]:
            gr.Warning(f"{label}: {new['label']}", title="Budget alert")


# ---------- Event handlers: lines ----------

def make_open(value):
    return lambda: value


def make_add(section):
    def add(user, user_budget, key, name, amount):
        updated = changed(user, user_budget, budget.add_item, key, section, name, amount)
        budget_alerts(user_budget, updated, key)
        return updated, "", ""
    return add


def make_update(section, index):
    def update(user, user_budget, key, name, amount):
        updated = changed(user, user_budget, budget.update_item, key, section, index, name, amount)
        budget_alerts(user_budget, updated, key)
        return updated, None
    return update


def make_remove(section, index):
    def remove(user, user_budget, key, open_section):
        updated = changed(user, user_budget, budget.remove_item, key, section, index)
        # An open edit row points at a line position that just moved, so close it; an add row can stay.
        return updated, open_section if open_section and open_section[0] == "add" else None
    return remove


# ---------- Event handlers: subcategories ----------

def make_confirm(keys):
    """Save every staged rename and move at once and close the pop-up. One bad name saves nothing."""
    def confirm(user, user_budget, *values):
        names, categories = values[:len(keys)], values[len(keys):]

        def apply(updated):
            for key, name, category in zip(keys, names, categories):
                budget.rename_subcategory(updated, key, name)
                budget.move_subcategory(updated, key, category)
        return changed(user, user_budget, apply), False
    return confirm


def make_remove_subcategory(key):
    def remove(user, user_budget):
        return changed(user, user_budget, budget.remove_subcategory, key)
    return remove


def add_subcategory(user, user_budget, name, category):
    return changed(user, user_budget, budget.add_subcategory, name, category)


# ---------- Event handlers: goals ----------

def dollars_text(cents):
    """Pre-fill for an amount box: "$1,800", or blank when not set."""
    return budget.format_money(cents) if cents else ""


def money_box(label, placeholder="$0.00", **options):
    """A text box that shows $ and commas as you type (design.MONEY_INPUT_SCRIPT)."""
    return gr.Textbox(label=label, placeholder=placeholder, elem_classes="sb-money-input", min_width=0, **options)


def target_texts(targets):
    """Pre-fill for the four target boxes: "50", "30", "10", "10", or blanks when off."""
    complete = set(targets) == set(budget.CATEGORIES)
    return [str(targets[category]) if complete else "" for category in budget.CATEGORIES]


def parse_field(label, text):
    try:
        return budget.parse_optional_amount(text)
    except ValueError as error:
        raise ValueError(f"{label}: {error}")


def plan_line_html(limit_text, *percent_texts):
    """Under the Goals boxes: what each typed % comes to in dollars of the monthly limit."""
    amounts = budget.plan_amounts(limit_text, percent_texts)
    parts = [f"{budget.CATEGORY_NAMES[category]} {budget.format_money(cents)}" for category, cents in amounts.items()]
    return f'<div class="sb-note">{" · ".join(parts)}</div>' if parts else ""


def set_plan(updated, limit_text, targets):
    """Store the monthly limit and the targets, and remember a plan was chosen so sign-in stops offering presets."""
    # A fresh dict, so the Needs and Wants limits from before they followed the targets don't linger.
    updated["settings"]["limits"] = {"overall": parse_field(MONTHLY_LIMIT, limit_text)}
    updated["settings"]["targets"] = targets
    updated["settings"]["plan_chosen"] = True


def plan_outputs(updated):
    """What a saved plan refreshes: the budget, the Goals limit and % boxes, and the auto-filled box (none now)."""
    settings = updated["settings"]
    return updated, dollars_text(settings["limits"]["overall"]), *target_texts(settings["targets"]), None


def save_plan(user, user_budget, limit_text, goal_text, needs, wants, investing, savings):
    """Save plan: the monthly limit, the savings goal and the four targets together."""
    def apply(updated):
        set_plan(updated, limit_text, budget.parse_targets(needs, wants, investing, savings))
        updated["settings"]["savings_goal"] = parse_field("Savings goal", goal_text)
    updated = changed(user, user_budget, apply)
    gr.Info("Plan saved" if updated["settings"]["targets"] else "Plan saved, targets off", title="Saved")
    return plan_outputs(updated)


def make_use_preset(preset):
    """The chooser's "Use this": save the preset's targets with the Goals tab's monthly limit, and close."""
    def use(user, user_budget, limit_text):
        updated = changed(user, user_budget, set_plan, limit_text, dict(preset["targets"]))
        gr.Info(f"{preset['name']} plan saved", title="Saved")
        return *plan_outputs(updated), gr.update(visible=False)
    return use


def set_own_plan(user, user_budget, limit_text):
    """The chooser's "Set my own": keep the Goals tab's monthly limit and the current targets, and close."""
    updated = changed(user, user_budget, lambda changing: set_plan(changing, limit_text, changing["settings"]["targets"]))
    return *plan_outputs(updated), gr.update(visible=False)


def preset_html(preset):
    """A preset's card in the chooser: its name, its four shares, why, and the research behind it."""
    split = " · ".join(f"{budget.CATEGORY_NAMES[category]} {preset['targets'][category]}%" for category in budget.CATEGORIES)
    return (
        f'<div class="sb-title">{escape(preset["name"])}</div><div class="sb-preset-split">{split}</div>'
        f'<div class="sb-note">{escape(preset["why"])}</div><div class="sb-source">{escape(preset["source"])}</div>'
    )


def make_complete(edited):
    """Typing in one target box: when three are filled, the fourth makes 100 and keeps doing so."""
    def complete(needs, wants, investing, savings, auto_key):
        typed = [needs, wants, investing, savings]
        filled, auto_key = budget.complete_targets(typed, auto_key, edited)
        # Only a box whose value really changes is updated, so no other box's change event fires for nothing.
        others = [new if new != old else gr.skip() for category, old, new in zip(budget.CATEGORIES, typed, filled) if category != edited]
        return *others, auto_key
    return complete


# ---------- Event handlers: history ----------

def zoom_choices_update(user_budget, pick):
    """The hidden zoom radio follows the subcategories; a pick that no longer exists goes back to everything."""
    if not user_budget:
        return gr.skip()
    choices = charts.zoom_choices(user_budget)
    return gr.update(choices=choices, value=pick if pick in {value for _, value in choices} else "all")


def history_view(user_budget, range_choice, pick):
    """The History tab for a range and a zoom: tiles, chart, biggest items, and whether to offer samples."""
    if not user_budget:
        return "", "", "", gr.update(visible=False), gr.update(visible=False)
    end_key, count = budget.history_range(user_budget, range_choice, budget.month_key())
    rows = budget.month_history(user_budget, end_key, count)
    valid = {value for _, value in charts.zoom_choices(user_budget)}
    view = charts.chart_view(user_budget, rows, pick if pick in valid else "all")
    items = charts.top_items_html(charts.top_items(user_budget, rows, view), view) if view["level"] != "all" else ""
    offer_samples = budget.months_with_data(user_budget) < SAMPLE_OFFER_BELOW
    return (
        charts.stat_tiles_html(rows, view), charts.history_chart(rows, view), items,
        gr.update(visible=bool(items)), gr.update(visible=offer_samples),
    )


def fill_samples(user, user_budget):
    updated = copy.deepcopy(user_budget)
    filled = budget.fill_sample_months(updated, budget.month_key())
    storage.save_budget(user, updated)
    gr.Info(f"Added {filled} sample months" if filled else "Those months already have data", title="Samples")
    return updated


# ---------- Event handlers: account ----------

def signed_in(key, user_budget):
    """Show the Budget tab for a freshly logged-in account, with Goals filled from its settings."""
    settings = user_budget["settings"]
    limit = dollars_text(settings["limits"].get("overall", 0))
    # Offered once: a new account picks a plan or sets its own, and either way it isn't asked again.
    ask_for_plan = not settings.get("plan_chosen") and not settings.get("targets")
    return (
        key, user_budget, budget.month_key(), None,
        gr.update(visible=False), gr.update(visible=True), gr.Tabs(selected="budget", visible=True),
        limit, dollars_text(settings["savings_goal"]),
        *target_texts(settings.get("targets", {})),
        "", "", "", gr.update(visible=ask_for_plan),
    )


def log_in(email_text, password):
    try:
        return signed_in(*storage.log_in(email_text, password))
    except ValueError as error:
        raise fail(str(error))


def create_account(name_text, email_text, password, confirm):
    try:
        return signed_in(*storage.create_account(name_text, email_text, password, confirm))
    except ValueError as error:
        raise fail(str(error))


def show_signup(showing):
    """Swap the auth card between Log in and Create account."""
    return gr.update(visible=not showing), gr.update(visible=showing)


def sign_out():
    return (
        None, None, budget.month_key(), None, gr.update(visible=True), gr.update(visible=False),
        *show_signup(False), False, gr.update(visible=False), gr.update(visible=False),
    )


def toggle_menu(menu_open):
    return not menu_open, gr.update(visible=not menu_open)


def open_profile(user_budget):
    """The profile page takes the tabs' place until Back."""
    account = user_budget["account"]
    return False, gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), account["name"], account["email"]


def save_profile(user, user_budget, name_text, email_text):
    """Change the name and the log-in email; a new email moves the saved file."""
    try:
        name = storage.clean_name(name_text)
        email = new_key = storage.clean_email(email_text)
        if new_key != user:
            storage.rename_budget(user, new_key)
    except ValueError as error:
        raise fail(str(error))
    updated = copy.deepcopy(user_budget)
    updated["account"].update(name=name, email=email)
    storage.save_budget(new_key, updated)
    gr.Info("Profile saved", title="Saved")
    return new_key, updated, email


def change_password(user, user_budget, current, new, confirm):
    if not storage.check_password(user_budget["account"], current):
        raise fail("Current password is wrong")
    if new != confirm:
        raise fail("The new passwords don't match")
    try:
        hashed = storage.new_password(new)
    except ValueError as error:
        raise fail(str(error))
    updated = copy.deepcopy(user_budget)
    updated["account"].update(hashed)
    storage.save_budget(user, updated)
    gr.Info("Password changed", title="Saved")
    return updated, "", "", ""


def delete_data(user):
    storage.delete_budget(user)
    gr.Info("Your data is deleted", title="Deleted")
    return (*sign_out(), gr.update(visible=False))


# ---------- Layout ----------

with gr.Blocks(title="Sliced Bread") as demo:
    user_state = gr.State(None)  # file key of the logged-in account: its email, "mark@example.com"
    budget_state = gr.State(None)  # that name's whole budget
    month_state = gr.State(budget.month_key())  # month on screen, "2026-10"
    open_state = gr.State(None)  # ("add", section) or ("edit", section, index): the one open form
    auto_target_state = gr.State(None)  # the target box filled in to make 100, until the user types in it
    menu_state = gr.State(False)  # whether the avatar's menu is open
    subs_open_state = gr.State(False)  # whether the subcategory pop-up is open

    # Log in with email and password, or create an account. Accounts are local JSON files, not a real auth service.
    with gr.Column(elem_classes="sb-card sb-auth") as auth_view:
        html(
            f'<div class="sb-auth-top">{design.duck_full(200)}<div class="sb-wordmark">Sliced Bread</div>'
            '<div class="sb-note">Know what is left to invest each month</div></div>'
        )
        with gr.Column(elem_classes="sb-auth-form") as login_panel:
            html('<div class="sb-title">Log in</div>')
            login_email = gr.Textbox(label="Email", placeholder="name@example.com", html_attributes=gr.InputHTMLAttributes(autocomplete="username"))
            login_password = gr.Textbox(label="Password", type="password", html_attributes=gr.InputHTMLAttributes(autocomplete="current-password"))
            login_button = gr.Button("Log in", variant="primary", elem_classes="sb-full")
            to_signup_button = gr.Button("New here? Create an account", elem_classes="sb-link-button")
        with gr.Column(visible=False, elem_classes="sb-auth-form") as signup_panel:
            html('<div class="sb-title">Create an account</div>')
            signup_name = gr.Textbox(label="Name", placeholder="Your name", html_attributes=gr.InputHTMLAttributes(autocomplete="name"))
            signup_email = gr.Textbox(label="Email", placeholder="name@example.com", html_attributes=gr.InputHTMLAttributes(autocomplete="username"))
            signup_password = gr.Textbox(
                label="Password", type="password", placeholder=f"At least {storage.MIN_PASSWORD_LENGTH} characters",
                html_attributes=gr.InputHTMLAttributes(autocomplete="new-password"),
            )
            signup_confirm = gr.Textbox(label="Password again", type="password", html_attributes=gr.InputHTMLAttributes(autocomplete="new-password"))
            signup_button = gr.Button("Create account", variant="primary", elem_classes="sb-full")
            to_login_button = gr.Button("Have an account? Log in", elem_classes="sb-link-button")

    with gr.Column(visible=False, elem_classes="sb-app") as app_view:
        # Header: logo left; the person's name and an avatar that opens a small menu, right.
        with gr.Row(elem_classes="sb-header"):
            html(f'<div class="sb-brand">{design.duck_mark(36)}<span class="sb-wordmark">Sliced Bread</span></div>', elem_classes="sb-grow")
            person_name = html("", elem_classes="sb-person")
            avatar_button = gr.Button("", elem_classes="sb-avatar-button", min_width=0, scale=0)
        with gr.Column(visible=False, elem_classes="sb-card sb-menu") as person_menu:
            edit_profile_button = gr.Button("Edit profile", elem_classes="sb-menu-item")
            sign_out_button = gr.Button("Sign out", elem_classes="sb-menu-item")

        with gr.Tabs() as app_tabs:
            with gr.Tab("Budget", id="budget"):
                # The hero card: month switcher on top, then the big number, the bar and the duck.
                with gr.Column(elem_classes="sb-card"):
                    with gr.Row(elem_classes="sb-hero-top"):
                        previous_month = gr.Button("‹", elem_classes="sb-icon sb-nav", min_width=0, scale=0)
                        month_title = html("", elem_classes="sb-grow")
                        next_month = gr.Button("›", elem_classes="sb-icon sb-nav", min_width=0, scale=0)

                    @gr.render(inputs=[budget_state, month_state], triggers=[budget_state.change, month_state.change])
                    def render_hero(user_budget, key):
                        if user_budget:
                            html(hero_html(user_budget, key))

                @gr.render(inputs=[budget_state, month_state, open_state], triggers=[budget_state.change, month_state.change, open_state.change])
                def render_budget(user_budget, key, open_section):
                    if not user_budget:
                        return
                    month = budget.get_month(user_budget, key)
                    opened = tuple(open_section) if open_section else None
                    split = split_html(user_budget, month)
                    if split:
                        with gr.Column(elem_classes="sb-card"):
                            html(split)

                    for section, section_name, category in sections(user_budget):
                        is_open = opened == ("add", section)
                        with gr.Column(elem_classes="sb-card"):
                            with gr.Row(elem_classes="sb-row"):
                                html(section_head_html(user_budget, month, section, section_name, category), elem_classes="sb-grow")
                                if not is_open:  # an open form closes with its own Done
                                    plus = gr.Button("+ Add", variant="primary", elem_classes="sb-add-button", min_width=0, scale=0)
                                    plus.click(make_open(("add", section)), outputs=open_state)

                            if is_open:
                                with gr.Column(elem_classes="sb-panel"):
                                    with gr.Row(elem_classes="sb-row"):
                                        name_box = gr.Textbox(
                                            label="Name", placeholder=NAME_PLACEHOLDERS.get(section, ""), autofocus=True, scale=3, min_width=0,
                                        )
                                        amount_box = money_box("Amount", scale=2)
                                    with gr.Row(elem_classes="sb-row"):
                                        add_button = gr.Button("Add", variant="primary")
                                        cancel_button = gr.Button("Done")
                                add_inputs = [user_state, budget_state, month_state, name_box, amount_box]
                                for trigger in (add_button.click, amount_box.submit, name_box.submit):
                                    trigger(make_add(section), inputs=add_inputs, outputs=[budget_state, name_box, amount_box])
                                cancel_button.click(lambda: None, outputs=open_state)

                            items = month[section]
                            if not items and not is_open:
                                html(f'<div class="sb-note">{EMPTY_STATES.get(section, CUSTOM_EMPTY_STATE)}</div>')
                            for index, item in enumerate(items):
                                if opened == ("edit", section, index):
                                    with gr.Column(elem_classes="sb-panel"):
                                        with gr.Row(elem_classes="sb-row"):
                                            edit_name = gr.Textbox(label="Name", value=item["name"], autofocus=True, interactive=True, scale=3, min_width=0)
                                            edit_amount = money_box("Amount", value=dollars_text(item["amount"]), interactive=True, scale=2)
                                        with gr.Row(elem_classes="sb-row"):
                                            save_button = gr.Button("Save", variant="primary")
                                            cancel_edit_button = gr.Button("Cancel")
                                    edit_inputs = [user_state, budget_state, month_state, edit_name, edit_amount]
                                    for trigger in (save_button.click, edit_name.submit, edit_amount.submit):
                                        trigger(make_update(section, index), inputs=edit_inputs, outputs=[budget_state, open_state])
                                    cancel_edit_button.click(lambda: None, outputs=open_state)
                                    continue
                                with gr.Row(elem_classes="sb-row sb-item"):
                                    html(design.line_html(item["name"], item["amount"]), elem_classes="sb-grow")
                                    edit = gr.Button("✎", elem_classes="sb-icon", min_width=0, scale=0)
                                    edit.click(make_open(("edit", section, index)), outputs=open_state)
                                    remove = gr.Button("✕", elem_classes="sb-icon", min_width=0, scale=0)
                                    remove.click(make_remove(section, index), inputs=[user_state, budget_state, month_state, open_state], outputs=[budget_state, open_state])

                    with gr.Column(elem_classes="sb-card sb-card-accent"):
                        html(savings_html(user_budget, key))

            with gr.Tab("History", id="history"):
                range_pick = gr.Radio(RANGE_CHOICES, value=RANGE_CHOICES[0], show_label=False, container=False, elem_classes="sb-pills")
                # Hidden: the chart's coloured pieces, legend and back link set it (design.HEAD's click script).
                zoom_pick = gr.Radio([(charts.ALL_CHOICE, "all")], value="all", show_label=False, container=False, elem_classes="sb-hidden sb-category-pick")
                with gr.Column(elem_classes="sb-card", visible=False) as sample_card:
                    html(
                        f'<div class="sb-duck-says" style="margin:0;padding:0;border:0">{design.duck_mark(44)}'
                        '<div class="sb-bubble">Only a month or two so far. Want sample months to see how this looks?</div></div>'
                    )
                    sample_button = gr.Button("Fill 5 sample months", variant="primary")
                history_tiles = html("")
                with gr.Column(elem_classes="sb-card"):
                    history_chart = html("")
                with gr.Column(elem_classes="sb-card", visible=False) as items_card:
                    history_items = html("")

            with gr.Tab("Goals", id="goals"):
                # The monthly limit times each % is that category's limit (Needs, Wants) or goal (Investing, Savings).
                with gr.Column(elem_classes="sb-card"):
                    html('<div class="sb-title">Your plan</div>')
                    limit_overall = money_box(MONTHLY_LIMIT, placeholder="No limit")
                    savings_goal = money_box("Savings goal", placeholder="No goal")
                    with gr.Row():
                        target_needs = gr.Textbox(label="Needs %", placeholder="Off", min_width=0)
                        target_wants = gr.Textbox(label="Wants %", placeholder="Off", min_width=0)
                    with gr.Row():
                        target_investing = gr.Textbox(label="Investing %", placeholder="Off", min_width=0)
                        target_savings = gr.Textbox(label="Savings %", placeholder="Off", min_width=0)
                    plan_line = html("")
                    with gr.Row():
                        choose_preset_button = gr.Button("Choose a preset")
                        save_plan_button = gr.Button("Save plan", variant="primary")
                    edit_subs_button = gr.Button("Edit subcategories")

        # The subcategory editor: a pop-up over the page from Goals' "Edit subcategories". Renames and moves wait for
        # Confirm; ✕ and Add subcategory save straight away.
        with gr.Column(visible=False, elem_classes="sb-modal") as subs_modal:
            with gr.Column(elem_classes="sb-card sb-modal-card"):
                html('<div class="sb-title">Subcategories</div>')

                @gr.render(inputs=[budget_state, subs_open_state], triggers=[budget_state.change, subs_open_state.change])
                def render_subcategories(user_budget, subs_open):
                    if not (user_budget and subs_open):
                        return
                    keys, name_boxes, move_boxes = [], [], []
                    for category in budget.CATEGORIES:
                        html(f'<div class="sb-group-head">{design.marker(category)}</div>')
                        for sub in budget.subcategories_in(user_budget, category):
                            with gr.Row(elem_classes="sb-row sb-sub-row"):
                                name_boxes.append(gr.Textbox(value=sub["name"], show_label=False, interactive=True, max_lines=1, scale=1, min_width=0))
                                move_boxes.append(gr.Dropdown(CATEGORY_OPTIONS, value=category, show_label=False, interactive=True, scale=0, min_width=CATEGORY_PICKER_WIDTH))
                                remove_button = gr.Button("✕", elem_classes="sb-icon", min_width=0, scale=0)
                                remove_button.click(make_remove_subcategory(sub["key"]), inputs=[user_state, budget_state], outputs=budget_state)
                            if sub["key"] in budget.PRESET_KEYS:
                                html('<span class="sb-preset-tag">Preset</span>')
                            keys.append(sub["key"])

                    with gr.Row(elem_classes="sb-row sb-add-sub"):
                        new_sub_name = gr.Textbox(label="New subcategory", placeholder="Pets", interactive=True, max_lines=1, scale=1, min_width=0)
                        new_sub_category = gr.Dropdown(CATEGORY_OPTIONS, value="wants", label="Counts toward", interactive=True, scale=0, min_width=CATEGORY_PICKER_WIDTH)
                    add_sub_button = gr.Button("Add subcategory")
                    for trigger in (add_sub_button.click, new_sub_name.submit):
                        trigger(add_subcategory, inputs=[user_state, budget_state, new_sub_name, new_sub_category], outputs=budget_state)

                    with gr.Row(elem_classes="sb-row"):
                        confirm_button = gr.Button("Confirm", variant="primary")
                        cancel_subs_button = gr.Button("Cancel")
                    confirm_button.click(make_confirm(keys), inputs=[user_state, budget_state, *name_boxes, *move_boxes], outputs=[budget_state, subs_open_state])
                    cancel_subs_button.click(lambda: False, outputs=subs_open_state)

        # The plan chooser: offered once after a new account's first sign-in, then from Goals' "Choose a preset".
        with gr.Column(visible=False, elem_classes="sb-modal") as plan_modal:
            with gr.Column(elem_classes="sb-card sb-modal-card"):
                html('<div class="sb-title">Pick a plan</div><div class="sb-note">You can change any number later on Goals.</div>')
                preset_buttons = []
                for preset in budget.PLAN_PRESETS:
                    with gr.Column(elem_classes="sb-panel"):
                        html(preset_html(preset))
                        preset_buttons.append((preset, gr.Button("Use this", variant="primary")))
                set_own_button = gr.Button("Set my own")

        # Opened from the avatar menu's "Edit profile" in place of the tabs. Not a tab: Gradio 6.31 folds a fourth tab
        # into a "more" menu even when it fits.
        with gr.Column(visible=False) as profile_view:
            profile_back_button = gr.Button("← Back", elem_classes="sb-back-button")
            with gr.Column(elem_classes="sb-card"):
                html('<div class="sb-title">Profile</div>')
                profile_name = gr.Textbox(label="Name", html_attributes=gr.InputHTMLAttributes(autocomplete="name"))
                profile_email = gr.Textbox(
                    label="Email", info="You log in with this", placeholder="name@example.com",
                    html_attributes=gr.InputHTMLAttributes(autocomplete="email"),
                )
                save_profile_button = gr.Button("Save profile", variant="primary")

            with gr.Column(elem_classes="sb-card"):
                html('<div class="sb-title">Change password</div>')
                current_password = gr.Textbox(label="Current password", type="password", html_attributes=gr.InputHTMLAttributes(autocomplete="current-password"))
                new_password = gr.Textbox(label="New password", type="password", placeholder=f"At least {storage.MIN_PASSWORD_LENGTH} characters", html_attributes=gr.InputHTMLAttributes(autocomplete="new-password"))
                confirm_password = gr.Textbox(label="New password again", type="password", html_attributes=gr.InputHTMLAttributes(autocomplete="new-password"))
                change_password_button = gr.Button("Change password", variant="primary")

            with gr.Column(elem_classes="sb-card sb-danger"):
                delete_button = gr.Button("Delete my data", variant="stop")
                with gr.Column(visible=False) as delete_confirm:
                    html('<div class="sb-note">This removes every month saved under your name. It cannot be undone.</div>')
                    with gr.Row():
                        confirm_delete_button = gr.Button("Delete for good", variant="stop")
                        keep_button = gr.Button("Keep my data")

    # ---------- Wiring ----------

    target_boxes = [target_needs, target_wants, target_investing, target_savings]
    session_outputs = [user_state, budget_state, month_state, open_state, auth_view, app_view]
    signed_in_outputs = session_outputs + [
        app_tabs, limit_overall, savings_goal, *target_boxes, login_password, signup_password, signup_confirm, plan_modal,
    ]
    signed_out_outputs = session_outputs + [login_panel, signup_panel, menu_state, person_menu, profile_view]

    for trigger in (login_button.click, login_email.submit, login_password.submit):
        trigger(log_in, inputs=[login_email, login_password], outputs=signed_in_outputs)
    for trigger in (signup_button.click, signup_name.submit, signup_email.submit, signup_password.submit, signup_confirm.submit):
        trigger(create_account, inputs=[signup_name, signup_email, signup_password, signup_confirm], outputs=signed_in_outputs)
    to_signup_button.click(lambda: show_signup(True), outputs=[login_panel, signup_panel])
    to_login_button.click(lambda: show_signup(False), outputs=[login_panel, signup_panel])

    # The header follows the budget's name.
    budget_state.change(lambda user_budget: (person_html(user_budget), initial(user_budget)), inputs=budget_state, outputs=[person_name, avatar_button])

    month_state.change(month_title_html, inputs=month_state, outputs=month_title)
    demo.load(month_title_html, inputs=month_state, outputs=month_title)
    previous_month.click(lambda key: (budget.shift_month(key, -1), None), inputs=month_state, outputs=[month_state, open_state])
    next_month.click(lambda key: (budget.shift_month(key, 1), None), inputs=month_state, outputs=[month_state, open_state])

    for target, box in zip(budget.CATEGORIES, target_boxes):
        others = [other for other_target, other in zip(budget.CATEGORIES, target_boxes) if other_target != target]
        # .change, not .input: Gradio 6.31 never sent this textbox's input event. complete_targets tells its own
        # update of the filled-in box apart from the user typing over it.
        box.change(
            make_complete(target), inputs=[*target_boxes, auto_target_state], outputs=[*others, auto_target_state],
            trigger_mode="always_last", show_progress="hidden",
        )
    for box in (limit_overall, *target_boxes):
        box.change(plan_line_html, inputs=[limit_overall, *target_boxes], outputs=plan_line, trigger_mode="always_last", show_progress="hidden")
    plan_saved_outputs = [budget_state, limit_overall, *target_boxes, auto_target_state]
    save_plan_button.click(save_plan, inputs=[user_state, budget_state, limit_overall, savings_goal, *target_boxes], outputs=plan_saved_outputs)
    choose_preset_button.click(lambda: gr.update(visible=True), outputs=plan_modal)
    for preset, button in preset_buttons:
        button.click(make_use_preset(preset), inputs=[user_state, budget_state, limit_overall], outputs=plan_saved_outputs + [plan_modal])
    set_own_button.click(set_own_plan, inputs=[user_state, budget_state, limit_overall], outputs=plan_saved_outputs + [plan_modal])
    edit_subs_button.click(lambda: True, outputs=subs_open_state)
    subs_open_state.change(lambda subs_open: gr.update(visible=subs_open), inputs=subs_open_state, outputs=subs_modal)

    history_outputs = [history_tiles, history_chart, history_items, items_card, sample_card]
    history_inputs = [budget_state, range_pick, zoom_pick]
    budget_state.change(zoom_choices_update, inputs=[budget_state, zoom_pick], outputs=zoom_pick).then(
        history_view, inputs=history_inputs, outputs=history_outputs,
    )
    for trigger in (range_pick.change, zoom_pick.change):
        trigger(history_view, inputs=history_inputs, outputs=history_outputs)
    sample_button.click(fill_samples, inputs=[user_state, budget_state], outputs=budget_state)

    avatar_button.click(toggle_menu, inputs=menu_state, outputs=[menu_state, person_menu])
    edit_profile_button.click(open_profile, inputs=budget_state, outputs=[menu_state, person_menu, profile_view, app_tabs, profile_name, profile_email])
    profile_back_button.click(lambda: (gr.update(visible=False), gr.update(visible=True)), outputs=[profile_view, app_tabs])
    sign_out_button.click(sign_out, outputs=signed_out_outputs)
    save_profile_button.click(save_profile, inputs=[user_state, budget_state, profile_name, profile_email], outputs=[user_state, budget_state, profile_email])
    change_password_button.click(
        change_password, inputs=[user_state, budget_state, current_password, new_password, confirm_password],
        outputs=[budget_state, current_password, new_password, confirm_password],
    )
    delete_button.click(lambda: gr.update(visible=True), outputs=delete_confirm)
    keep_button.click(lambda: gr.update(visible=False), outputs=delete_confirm)
    confirm_delete_button.click(delete_data, inputs=user_state, outputs=signed_out_outputs + [delete_confirm])


if __name__ == "__main__":
    demo.launch(theme=design.build_theme(), css=design.CSS, head=design.HEAD, share="--share" in sys.argv)  # Colab needs the public link
