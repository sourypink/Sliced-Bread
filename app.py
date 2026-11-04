"""Sliced Bread: a personal budget tracker. Run with: python app.py"""

import copy
import sys
from html import escape

import gradio as gr

import budget
import charts
import design
import storage

SECTION_NAMES = {
    "income": "Income",
    "necessities": "Necessities",
    "discretionary": "Discretionary",
    "travel": "Travel",
    "investments": "Investments",
    "savings": "Savings",
}
EMPTY_STATES = {
    "income": "No income yet. Add your salary, freelance or other pay.",
    "necessities": "Nothing yet. Add rent, groceries, gas.",
    "discretionary": "Nothing yet. Add movies, events, games, subscriptions.",
    "travel": "No trips yet. Add flights, hotels, food.",
    "investments": "Nothing yet. Add a tier like Retirement, then what you put in.",
}
NAME_PLACEHOLDERS = {
    "income": "Salary", "necessities": "Rent", "discretionary": "Concert tickets", "travel": "Flights", "investments": "Roth IRA",
}
LIMIT_LABELS = {"overall": "Monthly limit", **SECTION_NAMES}
TARGET_LABELS = {"needs": "Needs", "wants": "Wants", "investing": "Investing", "savings": "Savings"}
RANGE_CHOICES = ["6 months", "12 months", "All"]
CATEGORY_CHOICES = {
    "All spending": "all", "Necessities": "necessities", "Discretionary": "discretionary", "Travel": "travel",
    "Investments": "investments",
}
SAMPLE_OFFER_BELOW = 3  # months with data; under this, History offers sample months

def html(value, **options):
    return gr.HTML(value, padding=False, **options)


def fail(message):
    """Show a validation problem to the user without a traceback in the console."""
    return gr.Error(message, print_exception=False)


# ---------- Page pieces ----------

def header_html(display_name):
    """Logo and wordmark on the left, the signed-in name and its initial on the right."""
    return (
        f'<div class="sb-header"><div class="sb-brand">{design.duck_mark(36)}<span class="sb-wordmark">Sliced Bread</span></div>'
        f'<div class="sb-person"><span>{escape(display_name)}</span>'
        f'<span class="sb-avatar">{escape(display_name[:1].upper())}</span></div></div>'
    )


def month_title_html(key):
    return f'<div class="sb-month-label">{budget.month_label(key)}</div>'


def duck_line(user_budget, key):
    """What the duck says under the hero: one line picked from the month's state. The mascot's only job for now."""
    month = budget.get_month(user_budget, key)
    if budget.section_total(month, "income") == 0:
        return "Add your income and I'll do the math."
    left = budget.leftover(month)
    if left < 0:
        return "Quack. Spending and investing are over income this month."
    meters = watched_meters(user_budget, key)
    for label, result in meters.items():
        if result["state"] == "over":
            return f"Heads up: {label.lower()} is {result['label'].lower()}."
    for label, result in meters.items():
        if result["state"] == "warn":
            return f"Careful, {label.lower()} is near its limit."
    return f"Nice. {budget.format_money(left)} saved this month."


def hero_html(user_budget, key):
    """The big number, where the money went, and the duck."""
    month = budget.get_month(user_budget, key)
    income = budget.section_total(month, "income")
    expenses = budget.total_expenses(month)
    left = budget.leftover(month)
    name = budget.month_name(key)

    if left >= 0:
        top = f'<div class="sb-eyebrow">Left to save in {name}</div><div class="sb-hero-amount">{budget.format_money(left)}</div>'
    else:
        top = f'<div class="sb-eyebrow">Over budget in {name}</div><div class="sb-hero-amount sb-over">{budget.format_money(-left)}</div>'

    amounts = {section: budget.section_total(month, section) for section in budget.CHART_SECTIONS}
    amounts["savings"] = max(left, 0)
    whole = max(income, expenses + budget.total_invested(month))
    segments = "".join(
        f'<span style="flex:{cents / whole:.4f};background:{design.SECTION_COLORS[section]}"></span>'
        for section, cents in amounts.items() if cents
    ) or '<span class="sb-bar-empty"></span>'
    key_items = "".join(
        f"<span>{design.dot(section)}{SECTION_NAMES[section]} {design.money(cents)}</span>"
        for section, cents in amounts.items() if cents
    )
    limit = user_budget["settings"]["limits"]["overall"]
    limit_meter = design.meter_html(
        budget.meter(expenses, limit), f"Spent {budget.format_money(expenses)} of {budget.format_money(limit)}"
    )
    duck = (
        f'<div class="sb-duck-says"><span class="sb-bob">{design.duck_mark(44)}</span>'
        f'<div class="sb-bubble">{escape(duck_line(user_budget, key))}</div></div>'
    )
    return (
        f'{top}<div class="sb-bar">{segments}</div><div class="sb-key">{key_items}</div>'
        + (f'<div style="margin-top:16px">{limit_meter}</div>' if limit_meter else "")
        + duck
    )


def section_head_html(user_budget, month, section):
    total = budget.section_total(month, section)
    limit = user_budget["settings"]["limits"].get(section, 0)
    of_limit = f'<span class="sb-note">of {budget.format_money(limit)}</span>' if limit else ""
    return (
        f'<div class="sb-head"><div class="sb-title">{design.dot(section)}{SECTION_NAMES[section]}</div>'
        f'<div class="sb-head-total">{design.money(total)}{of_limit}</div></div>'
    )


def tier_head_html(tier, cents):
    return f'<div class="sb-tier"><span>{escape(tier)}</span>{design.money(cents)}</div>'


def tier_box(user_budget, value=""):
    """Type a tier: an existing one (the placeholder lists them) or a new name, which creates it."""
    used = budget.tiers(user_budget)
    hint = ", ".join(used) if used else "Retirement"
    return gr.Textbox(label="Tier", value=value, placeholder=hint, autofocus=not value, min_width=0, elem_classes="sb-tier-box")


def savings_html(user_budget, key):
    left = budget.leftover(budget.get_month(user_budget, key))
    head = f'<div class="sb-title">{design.dot("savings")}Savings</div>'
    amount = f'<div class="sb-big" style="margin-top:12px">{budget.format_money(max(left, 0))}</div>'
    if left < 0:
        note = f'<div class="sb-note" style="color:var(--sb-over)">Over budget by {budget.format_money(-left)}. Nothing left to save.</div>'
    else:
        note = '<div class="sb-note">Whatever is left after spending and investing lands here.</div>'
    goal = user_budget["settings"]["savings_goal"]
    if goal:
        savings = design.progress_html(budget.savings_progress(user_budget), goal)
    else:
        savings = '<div class="sb-note">Set a savings goal on the Account tab.</div>'
    return f'{head}{amount}<div style="margin-top:6px">{note}</div><div style="margin-top:16px">{savings}</div>'


def split_html(user_budget, month):
    """Needs, wants and savings against the user's percentage targets. Empty when targets are off."""
    targets = user_budget["settings"].get("targets", {})
    meters = budget.target_meters(targets, month)
    if not meters:
        return ""
    plan = "/".join(str(targets[key]) for key in budget.TARGET_KEYS)
    rows = "".join(
        design.meter_html(result, f"{TARGET_LABELS[key]} {result['actual_percent']}% of {result['target_percent']}%")
        for key, result in meters.items()
    )
    return f'<div class="sb-title">Your {plan} split</div><div class="sb-split">{rows}</div>'


def watched_meters(user_budget, key):
    """Every limit and target an alert watches, by the name the alert shows."""
    month = budget.get_month(user_budget, key)
    limits = user_budget["settings"]["limits"]
    spent = {"overall": budget.total_expenses(month)}
    spent.update({section: budget.section_total(month, section) for section in budget.EXPENSE_SECTIONS})
    meters = {LIMIT_LABELS[limit_key]: budget.meter(spent[limit_key], limits[limit_key]) for limit_key in budget.LIMIT_KEYS}
    targets = budget.target_meters(user_budget["settings"].get("targets", {}), month)
    # Only needs and wants are limits; investing and savings are minimums, so they never alert.
    meters.update({f"{TARGET_LABELS[target]} target": result for target, result in targets.items() if target in budget.TARGET_GROUPS})
    return meters


def budget_alerts(before, after, key):
    """Warn when a change pushes a limit or target into "near" or "over"."""
    old = watched_meters(before, key)
    for label, new in watched_meters(after, key).items():
        if new["state"] in ("warn", "over") and new["state"] != old.get(label, {"state": "none"})["state"]:
            gr.Warning(f"{label}: {new['label']}", title="Budget alert")


# ---------- Event handlers ----------

def make_toggle(section):
    def toggle(open_section):
        return None if open_section == ("add", section) else ("add", section)
    return toggle


def make_open(value):
    return lambda: value


def make_add(section):
    def add(user, user_budget, key, name, amount, tier=None):
        updated = copy.deepcopy(user_budget)
        try:
            budget.add_item(updated, key, section, name, amount, tier)
        except ValueError as error:
            raise fail(str(error))
        storage.save_budget(user, updated)
        budget_alerts(user_budget, updated, key)
        return updated, "", ""
    return add


def make_update(section, index):
    def update(user, user_budget, key, name, amount, tier=None):
        updated = copy.deepcopy(user_budget)
        try:
            budget.update_item(updated, key, section, index, name, amount, tier)
        except ValueError as error:
            raise fail(str(error))
        storage.save_budget(user, updated)
        budget_alerts(user_budget, updated, key)
        return updated, None
    return update


def make_remove(section, index):
    def remove(user, user_budget, key, open_section):
        updated = copy.deepcopy(user_budget)
        budget.remove_item(updated, key, section, index)
        storage.save_budget(user, updated)
        # An open edit row points at a line position that just moved, so close it; an add row can stay.
        return updated, open_section if open_section and open_section[0] == "add" else None
    return remove


def dollars_text(cents):
    """Pre-fill for a limit box: "1,800", or blank when not set."""
    return budget.format_money(cents).removeprefix("$") if cents else ""


def sign_in(name_text):
    """Demo mode: any name opens that name's budget, and the password box is not checked."""
    try:
        name = storage.clean_name(name_text)
        key = storage.file_key(name)
    except ValueError as error:
        raise fail(str(error))
    user_budget = storage.load_budget(key)
    settings = user_budget["settings"]
    return (
        key, user_budget, budget.month_key(), None,
        gr.update(visible=False), gr.update(visible=True),
        header_html(name), gr.Tabs(selected="budget"),
        *[dollars_text(settings["limits"][limit]) for limit in budget.LIMIT_KEYS],
        dollars_text(settings["savings_goal"]),
        *target_texts(settings.get("targets", {})),
        "",
    )


def target_texts(targets):
    """Pre-fill for the four target boxes: "50", "30", "10", "10", or blanks when off."""
    complete = set(targets) == set(budget.TARGET_KEYS)
    return [str(targets[key]) if complete else "" for key in budget.TARGET_KEYS]


def sign_out():
    return None, None, budget.month_key(), None, gr.update(visible=True), gr.update(visible=False), "", ""


def save_settings(user, user_budget, overall, necessities, discretionary, travel, goal):
    updated = copy.deepcopy(user_budget)
    typed = dict(zip(budget.LIMIT_KEYS, (overall, necessities, discretionary, travel)))
    try:
        for key, text in typed.items():
            updated["settings"]["limits"][key] = parse_field(LIMIT_LABELS[key], text)
        updated["settings"]["savings_goal"] = parse_field("Savings goal", goal)
    except ValueError as error:
        raise fail(str(error))
    storage.save_budget(user, updated)
    gr.Info("Limits and goal saved", title="Saved")
    return updated


def save_targets(user, user_budget, needs, wants, investing, savings):
    try:
        targets = budget.parse_targets(needs, wants, investing, savings)
    except ValueError as error:
        raise fail(str(error))
    updated = copy.deepcopy(user_budget)
    updated["settings"]["targets"] = targets
    storage.save_budget(user, updated)
    gr.Info("Targets saved" if targets else "Targets turned off", title="Saved")
    return updated, *target_texts(targets)


def use_50_30_20(user, user_budget):
    return save_targets(user, user_budget, *(str(percent) for percent in budget.RULE_50_30_20.values()))


def parse_field(label, text):
    try:
        return budget.parse_optional_amount(text)
    except ValueError as error:
        raise ValueError(f"{label}: {error}")


def history_view(user_budget, range_choice, category_choice):
    """The History tab for a range and a category: tiles, chart, biggest items, and whether to offer samples."""
    if not user_budget:
        return "", "", "", gr.update(visible=False), gr.update(visible=False)
    category = CATEGORY_CHOICES[category_choice]
    end_key, count = budget.history_range(user_budget, range_choice, budget.month_key())
    rows = budget.month_history(user_budget, end_key, count)
    items = ""
    if category in charts.SECTION_NAMES:
        items = charts.top_items_html(budget.top_items(user_budget, [row["key"] for row in rows], category), category)
    offer_samples = budget.months_with_data(user_budget) < SAMPLE_OFFER_BELOW
    return (
        charts.stat_tiles_html(rows, category), charts.history_chart(rows, category), items,
        gr.update(visible=bool(items)), gr.update(visible=offer_samples),
    )


def fill_samples(user, user_budget):
    updated = copy.deepcopy(user_budget)
    filled = budget.fill_sample_months(updated, budget.month_key())
    storage.save_budget(user, updated)
    gr.Info(f"Added {filled} sample months" if filled else "Those months already have data", title="Samples")
    return updated


def delete_data(user):
    storage.delete_budget(user)
    gr.Info("Your data is deleted", title="Deleted")
    return (*sign_out(), gr.update(visible=False))


# ---------- Layout ----------

with gr.Blocks(title="Sliced Bread") as demo:
    user_state = gr.State(None)  # file key of the signed-in name, "mark_g"
    budget_state = gr.State(None)  # that name's whole budget
    month_state = gr.State(budget.month_key())  # month on screen, "2026-10"
    open_state = gr.State(None)  # ("add", section) or ("edit", section, index): the one open form

    # Sign in: demo mode, any name and password work
    with gr.Column(elem_classes="sb-card sb-auth") as auth_view:
        html(
            f'<div class="sb-auth-top">{design.duck_full(200)}<div class="sb-wordmark">Sliced Bread</div>'
            '<div class="sb-note">Know what is left to invest each month</div>'
            '<span class="sb-chip">Demo: any name and password work</span></div>'
        )
        login_username = gr.Textbox(label="Name", placeholder="Your name", html_attributes=gr.InputHTMLAttributes(autocomplete="username"))
        login_password = gr.Textbox(label="Password", type="password", placeholder="Anything", html_attributes=gr.InputHTMLAttributes(autocomplete="current-password"))
        login_button = gr.Button("Sign in", variant="primary", elem_classes="sb-full")

    with gr.Column(visible=False) as app_view:
        greeting = html("")

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

                    for section in budget.SECTIONS:
                        is_open = opened == ("add", section)
                        with gr.Column(elem_classes="sb-card"):
                            with gr.Row(elem_classes="sb-row"):
                                html(section_head_html(user_budget, month, section), elem_classes="sb-grow")
                                plus = gr.Button(
                                    "Close" if is_open else "+ Add", variant="secondary" if is_open else "primary",
                                    elem_classes="sb-add-button", min_width=0, scale=0,
                                )
                                plus.click(make_toggle(section), inputs=open_state, outputs=open_state)

                            limit = user_budget["settings"]["limits"].get(section, 0)
                            meter = design.meter_html(budget.meter(budget.section_total(month, section), limit))
                            if meter:
                                html(meter)

                            if is_open:
                                with gr.Column(elem_classes="sb-panel"):
                                    # Start in the tier last used this month, so several lines go in one after another.
                                    last_tier = month[section][-1]["tier"] if section == budget.TIERED_SECTION and month[section] else ""
                                    tier_input = tier_box(user_budget, last_tier) if section == budget.TIERED_SECTION else None
                                    with gr.Row(elem_classes="sb-row"):
                                        name_box = gr.Textbox(
                                            label="Name", placeholder=NAME_PLACEHOLDERS[section], autofocus=tier_input is None or bool(last_tier),
                                            scale=3, min_width=0,
                                        )
                                        amount_box = gr.Textbox(label="Amount", placeholder="0.00", scale=2, min_width=0)
                                    with gr.Row(elem_classes="sb-row"):
                                        add_button = gr.Button("Add", variant="primary")
                                        cancel_button = gr.Button("Done")
                                add_inputs = [user_state, budget_state, month_state, name_box, amount_box] + ([tier_input] if tier_input else [])
                                for trigger in (add_button.click, amount_box.submit, name_box.submit):
                                    trigger(make_add(section), inputs=add_inputs, outputs=[budget_state, name_box, amount_box])
                                cancel_button.click(lambda: None, outputs=open_state)

                            items = month[section]
                            if not items and not is_open:
                                html(f'<div class="sb-note">{EMPTY_STATES[section]}</div>')
                            # Investment lines show under their tier; each keeps its real position for edit and delete.
                            groups = [(None, list(enumerate(items)))]
                            if section == budget.TIERED_SECTION:
                                names = list(dict.fromkeys(item["tier"] for item in items))
                                groups = [(tier, [(i, item) for i, item in enumerate(items) if item["tier"] == tier]) for tier in names]
                            for tier, lines in groups:
                                if tier:
                                    html(tier_head_html(tier, sum(item["amount"] for _, item in lines)))
                                for index, item in lines:
                                    if opened == ("edit", section, index):
                                        with gr.Column(elem_classes="sb-panel"):
                                            edit_tier = tier_box(user_budget, item["tier"]) if tier else None
                                            with gr.Row(elem_classes="sb-row"):
                                                edit_name = gr.Textbox(label="Name", value=item["name"], autofocus=True, scale=3, min_width=0)
                                                edit_amount = gr.Textbox(label="Amount", value=dollars_text(item["amount"]), scale=2, min_width=0)
                                            with gr.Row(elem_classes="sb-row"):
                                                save_button = gr.Button("Save", variant="primary")
                                                cancel_edit_button = gr.Button("Cancel")
                                        edit_inputs = [user_state, budget_state, month_state, edit_name, edit_amount] + ([edit_tier] if edit_tier else [])
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
                category_pick = gr.Radio(list(CATEGORY_CHOICES), value="All spending", show_label=False, container=False, elem_classes="sb-pills")
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

            with gr.Tab("Account", id="account"):
                with gr.Column(elem_classes="sb-card"):
                    html('<div class="sb-title">Monthly limits</div><div class="sb-note">Leave blank for no limit.</div>')
                    with gr.Row():
                        limit_overall = gr.Textbox(label="Monthly limit", placeholder="No limit", min_width=120)
                        limit_necessities = gr.Textbox(label="Necessities", placeholder="No limit", min_width=120)
                    with gr.Row():
                        limit_discretionary = gr.Textbox(label="Discretionary", placeholder="No limit", min_width=120)
                        limit_travel = gr.Textbox(label="Travel", placeholder="No limit", min_width=120)
                    savings_goal = gr.Textbox(label="Savings goal", placeholder="No goal")
                    save_limits_button = gr.Button("Save limits and goal", variant="primary")

                with gr.Column(elem_classes="sb-card"):
                    html(
                        '<div class="sb-title">Percentage targets</div><div class="sb-note">Needs are necessities, '
                        "wants are discretionary and travel, investing is your Investments section, savings is what is left. "
                        "Leave blank to turn off.</div>"
                    )
                    with gr.Row():
                        target_needs = gr.Textbox(label="Needs %", placeholder="Off", min_width=0)
                        target_wants = gr.Textbox(label="Wants %", placeholder="Off", min_width=0)
                    with gr.Row():
                        target_investing = gr.Textbox(label="Investing %", placeholder="Off", min_width=0)
                        target_savings = gr.Textbox(label="Savings %", placeholder="Off", min_width=0)
                    with gr.Row():
                        use_rule_button = gr.Button("Use 50/30/20")
                        save_targets_button = gr.Button("Save targets", variant="primary")

                with gr.Column(elem_classes="sb-card sb-danger"):
                    sign_out_button = gr.Button("Sign out")
                    delete_button = gr.Button("Delete my data", variant="stop")
                    with gr.Column(visible=False) as delete_confirm:
                        html('<div class="sb-note">This removes every month saved under your name. It cannot be undone.</div>')
                        with gr.Row():
                            confirm_delete_button = gr.Button("Delete for good", variant="stop")
                            keep_button = gr.Button("Keep my data")

    # ---------- Wiring ----------

    limit_boxes = [limit_overall, limit_necessities, limit_discretionary, limit_travel]
    session_outputs = [user_state, budget_state, month_state, open_state, auth_view, app_view]
    target_boxes = [target_needs, target_wants, target_investing, target_savings]
    signed_in_outputs = session_outputs + [greeting, app_tabs, *limit_boxes, savings_goal, *target_boxes, login_password]

    for trigger in (login_button.click, login_username.submit, login_password.submit):
        trigger(sign_in, inputs=login_username, outputs=signed_in_outputs)

    month_state.change(month_title_html, inputs=month_state, outputs=month_title)
    demo.load(month_title_html, inputs=month_state, outputs=month_title)
    previous_month.click(lambda key: (budget.shift_month(key, -1), None), inputs=month_state, outputs=[month_state, open_state])
    next_month.click(lambda key: (budget.shift_month(key, 1), None), inputs=month_state, outputs=[month_state, open_state])

    save_limits_button.click(save_settings, inputs=[user_state, budget_state, *limit_boxes, savings_goal], outputs=budget_state)
    save_targets_button.click(save_targets, inputs=[user_state, budget_state, *target_boxes], outputs=[budget_state, *target_boxes])
    use_rule_button.click(use_50_30_20, inputs=[user_state, budget_state], outputs=[budget_state, *target_boxes])

    history_outputs = [history_tiles, history_chart, history_items, items_card, sample_card]
    for trigger in (budget_state.change, range_pick.change, category_pick.change):
        trigger(history_view, inputs=[budget_state, range_pick, category_pick], outputs=history_outputs)
    sample_button.click(fill_samples, inputs=[user_state, budget_state], outputs=budget_state)

    sign_out_button.click(sign_out, outputs=session_outputs + [greeting, login_password])
    delete_button.click(lambda: gr.update(visible=True), outputs=delete_confirm)
    keep_button.click(lambda: gr.update(visible=False), outputs=delete_confirm)
    confirm_delete_button.click(delete_data, inputs=user_state, outputs=session_outputs + [greeting, login_password, delete_confirm])


if __name__ == "__main__":
    demo.launch(theme=design.build_theme(), css=design.CSS, head=design.HEAD, share="--share" in sys.argv)  # Colab needs the public link
