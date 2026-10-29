"""Sliced Bread: a personal budget tracker. Run with: python app.py"""

import copy
import sys
from html import escape

import gradio as gr

import budget
import design
import storage

SECTION_NAMES = {
    "income": "Income",
    "necessities": "Necessities",
    "discretionary": "Discretionary",
    "travel": "Travel",
    "investments": "Investments",
}
EMPTY_STATES = {
    "income": "No income yet. Add your salary, freelance or other pay.",
    "necessities": "Nothing yet. Add rent, groceries, gas.",
    "discretionary": "Nothing yet. Add movies, events, games, subscriptions.",
    "travel": "No trips yet. Add flights, hotels, food.",
}
NAME_PLACEHOLDERS = {"income": "Salary", "necessities": "Rent", "discretionary": "Concert tickets", "travel": "Flights"}
LIMIT_LABELS = {"overall": "Monthly limit", **SECTION_NAMES}
TARGET_LABELS = {"needs": "Needs", "wants": "Wants", "savings": "Savings"}

def html(value, **options):
    return gr.HTML(value, padding=False, **options)


def fail(message):
    """Show a validation problem to the user without a traceback in the console."""
    return gr.Error(message, print_exception=False)


# ---------- Page pieces ----------

def header_html(display_name):
    return f'<div class="sb-head"><div class="sb-brand">Sliced Bread</div><div class="sb-note">Hi, {escape(display_name)}</div></div>'


def hero_html(user_budget, key):
    """The one hero line plus where the money went."""
    month = budget.get_month(user_budget, key)
    income = budget.section_total(month, "income")
    expenses = budget.total_expenses(month)
    left = budget.leftover(month)
    name = budget.month_name(key)

    if income == 0 and expenses == 0:
        return f'<div class="sb-hero">Add your income to plan {name}</div>'
    if left >= 0:
        title = f'<div class="sb-hero">{design.money(left)} left to invest in {name}</div>'
    else:
        title = f'<div class="sb-hero sb-over">Over budget by {design.money(-left)} in {name}</div>'

    amounts = {section: budget.section_total(month, section) for section in budget.EXPENSE_SECTIONS}
    amounts["investments"] = max(left, 0)
    whole = max(income, expenses)
    segments = "".join(
        f'<span style="width:{cents / whole * 100:.2f}%;background:{design.SECTION_COLORS[section]}"></span>'
        for section, cents in amounts.items() if cents
    )
    key_items = "".join(
        f"<span>{design.dot(section)}{SECTION_NAMES[section]} {design.money(cents)}</span>"
        for section, cents in amounts.items() if cents
    )
    limit = user_budget["settings"]["limits"]["overall"]
    limit_meter = design.meter_html(
        budget.meter(expenses, limit), f"Spent {budget.format_money(expenses)} of {budget.format_money(limit)}"
    )
    return f'{title}<div class="sb-bar">{segments}</div><div class="sb-key">{key_items}</div>' + (
        f'<div style="margin-top:16px">{limit_meter}</div>' if limit_meter else ""
    )


def section_head_html(user_budget, month, section):
    total = budget.section_total(month, section)
    limit = user_budget["settings"]["limits"].get(section, 0)
    amount = design.money(total)
    if limit:
        amount = f'<span class="sb-money">{budget.format_money(total)} of {budget.format_money(limit)}</span>'
    return f'<div class="sb-head"><div class="sb-title">{design.dot(section)}{SECTION_NAMES[section]}</div>{amount}</div>'


def investments_html(user_budget, key):
    left = budget.leftover(budget.get_month(user_budget, key))
    head = (
        f'<div class="sb-head"><div class="sb-title">{design.dot("investments")}Investments</div>'
        f"{design.money(max(left, 0))}</div>"
    )
    if left < 0:
        note = f'<div class="sb-note" style="color:var(--sb-over)">Over budget by {budget.format_money(-left)}. Nothing left to invest.</div>'
    else:
        note = '<div class="sb-note">Whatever is left after spending goes here.</div>'
    goal = user_budget["settings"]["savings_goal"]
    if goal:
        savings = design.progress_html(budget.savings_progress(user_budget), goal)
    else:
        savings = '<div class="sb-note">Set a savings goal on the Account tab.</div>'
    return f'{head}{note}<div style="margin-top:8px">{savings}</div>'


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
    meters.update({f"{TARGET_LABELS[target]} target": result for target, result in targets.items() if target != "savings"})
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
    def add(user, user_budget, key, name, amount):
        updated = copy.deepcopy(user_budget)
        try:
            budget.add_item(updated, key, section, name, amount)
        except ValueError as error:
            raise fail(str(error))
        storage.save_budget(user, updated)
        budget_alerts(user_budget, updated, key)
        return updated, "", ""
    return add


def make_update(section, index):
    def update(user, user_budget, key, name, amount):
        updated = copy.deepcopy(user_budget)
        try:
            budget.update_item(updated, key, section, index, name, amount)
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


def signed_in(username):
    """Everything the screen needs once someone is in: states, views and account fields."""
    user_budget = storage.load_budget(username)
    settings = user_budget["settings"]
    display_name = storage.get_display_name(username)
    return (
        username, user_budget, budget.month_key(), None,
        gr.update(visible=False), gr.update(visible=True),
        header_html(display_name),
        display_name,
        *[dollars_text(settings["limits"][key]) for key in budget.LIMIT_KEYS],
        dollars_text(settings["savings_goal"]),
        *target_texts(settings.get("targets", {})),
        "", "",
    )


def target_texts(targets):
    """Pre-fill for the three target boxes: "50", "30", "20", or blanks when off."""
    return [str(targets[key]) if targets else "" for key in budget.TARGET_KEYS]


def sign_in(username, password):
    try:
        return signed_in(storage.sign_in(username, password))
    except ValueError as error:
        raise fail(str(error))


def create_account(display_name, username, password):
    try:
        return signed_in(storage.create_account(username, password, display_name))
    except ValueError as error:
        raise fail(str(error))


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


def save_targets(user, user_budget, needs, wants, savings):
    try:
        targets = budget.parse_targets(needs, wants, savings)
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


def save_display_name(user, display_name):
    storage.set_display_name(user, display_name)
    gr.Info("Name saved", title="Saved")
    name = storage.get_display_name(user)
    return header_html(name), name


def change_password(user, current, new):
    try:
        storage.change_password(user, current, new)
    except ValueError as error:
        raise fail(str(error))
    gr.Info("Password changed", title="Saved")
    return "", ""


def delete_account(user):
    storage.delete_account(user)
    gr.Info("Account and data deleted", title="Deleted")
    return (*sign_out(), gr.update(visible=False))


# ---------- Layout ----------

with gr.Blocks(title="Sliced Bread") as demo:
    user_state = gr.State(None)  # signed-in username
    budget_state = gr.State(None)  # that user's whole budget
    month_state = gr.State(budget.month_key())  # month on screen, "2026-10"
    open_state = gr.State(None)  # ("add", section) or ("edit", section, index): the one open form

    # Sign in / create account
    with gr.Column(elem_classes="sb-card") as auth_view:
        html('<div class="sb-brand">Sliced Bread</div><div class="sb-subtitle">Know what is left to invest each month</div>')
        with gr.Tabs():
            with gr.Tab("Sign in"):
                login_username = gr.Textbox(label="Username", html_attributes=gr.InputHTMLAttributes(autocomplete="username", autocapitalize="off"))
                login_password = gr.Textbox(label="Password", type="password", html_attributes=gr.InputHTMLAttributes(autocomplete="current-password"))
                login_button = gr.Button("Sign in", variant="primary")
            with gr.Tab("Create account"):
                new_display_name = gr.Textbox(label="Your name")
                new_username = gr.Textbox(label="Username", placeholder="3-20 letters, numbers or _", html_attributes=gr.InputHTMLAttributes(autocomplete="username", autocapitalize="off"))
                new_password = gr.Textbox(label="Password", type="password", placeholder="At least 6 characters", html_attributes=gr.InputHTMLAttributes(autocomplete="new-password"))
                create_button = gr.Button("Create account", variant="primary")

    with gr.Column(visible=False) as app_view:
        greeting = html("")

        with gr.Tabs():
            with gr.Tab("Budget"):
                with gr.Row(elem_classes="sb-month"):
                    previous_month = gr.Button("‹", elem_classes="sb-x", min_width=0, scale=0)
                    month_title = html("", elem_classes="sb-grow")
                    next_month = gr.Button("›", elem_classes="sb-x", min_width=0, scale=0)

                @gr.render(inputs=[budget_state, month_state, open_state], triggers=[budget_state.change, month_state.change, open_state.change])
                def render_budget(user_budget, key, open_section):
                    if not user_budget:
                        return
                    month = budget.get_month(user_budget, key)
                    opened = tuple(open_section) if open_section else None
                    with gr.Column(elem_classes="sb-card"):
                        html(hero_html(user_budget, key))
                    split = split_html(user_budget, month)
                    if split:
                        with gr.Column(elem_classes="sb-card"):
                            html(split)

                    for section in budget.SECTIONS:
                        is_open = opened == ("add", section)
                        with gr.Column(elem_classes="sb-card"):
                            with gr.Row(elem_classes="sb-row"):
                                html(section_head_html(user_budget, month, section), elem_classes="sb-grow")
                                plus = gr.Button("−" if is_open else "+", variant="primary", elem_classes="sb-plus", min_width=0, scale=0)
                                plus.click(make_toggle(section), inputs=open_state, outputs=open_state)

                            limit = user_budget["settings"]["limits"].get(section, 0)
                            meter = design.meter_html(budget.meter(budget.section_total(month, section), limit))
                            if meter:
                                html(meter)

                            if is_open:
                                with gr.Column(elem_classes="sb-add"):
                                    with gr.Row(elem_classes="sb-row"):
                                        name_box = gr.Textbox(label="Name", placeholder=NAME_PLACEHOLDERS[section], autofocus=True, scale=3, min_width=0)
                                        amount_box = gr.Textbox(label="Amount", placeholder="0.00", scale=2, min_width=0)
                                    with gr.Row(elem_classes="sb-row"):
                                        add_button = gr.Button("Add", variant="primary")
                                        cancel_button = gr.Button("Done")
                                add_inputs = [user_state, budget_state, month_state, name_box, amount_box]
                                for trigger in (add_button.click, amount_box.submit, name_box.submit):
                                    trigger(make_add(section), inputs=add_inputs, outputs=[budget_state, name_box, amount_box])
                                cancel_button.click(lambda: None, outputs=open_state)

                            items = month[section]
                            if not items and not is_open:
                                html(f'<div class="sb-note">{EMPTY_STATES[section]}</div>')
                            for index, item in enumerate(items):
                                if opened == ("edit", section, index):
                                    with gr.Column(elem_classes="sb-add"):
                                        with gr.Row(elem_classes="sb-row"):
                                            edit_name = gr.Textbox(label="Name", value=item["name"], autofocus=True, scale=3, min_width=0)
                                            edit_amount = gr.Textbox(label="Amount", value=dollars_text(item["amount"]), scale=2, min_width=0)
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
                                    edit = gr.Button("✎", elem_classes="sb-x", min_width=0, scale=0)
                                    edit.click(make_open(("edit", section, index)), outputs=open_state)
                                    remove = gr.Button("✕", elem_classes="sb-x", min_width=0, scale=0)
                                    remove.click(make_remove(section, index), inputs=[user_state, budget_state, month_state, open_state], outputs=[budget_state, open_state])

                    with gr.Column(elem_classes="sb-card"):
                        html(investments_html(user_budget, key))

            with gr.Tab("Account"):
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
                        "wants are discretionary and travel, savings is what is left. Leave blank to turn off.</div>"
                    )
                    with gr.Row():
                        target_needs = gr.Textbox(label="Needs %", placeholder="Off", min_width=80)
                        target_wants = gr.Textbox(label="Wants %", placeholder="Off", min_width=80)
                        target_savings = gr.Textbox(label="Savings %", placeholder="Off", min_width=80)
                    with gr.Row():
                        use_rule_button = gr.Button("Use 50/30/20")
                        save_targets_button = gr.Button("Save targets", variant="primary")

                with gr.Column(elem_classes="sb-card"):
                    html('<div class="sb-title">Profile</div>')
                    display_name = gr.Textbox(label="Your name")
                    save_name_button = gr.Button("Save name")

                with gr.Column(elem_classes="sb-card"):
                    html('<div class="sb-title">Password</div>')
                    current_password = gr.Textbox(label="Current password", type="password", html_attributes=gr.InputHTMLAttributes(autocomplete="current-password"))
                    changed_password = gr.Textbox(label="New password", type="password", html_attributes=gr.InputHTMLAttributes(autocomplete="new-password"))
                    change_password_button = gr.Button("Change password")

                with gr.Column(elem_classes="sb-card"):
                    sign_out_button = gr.Button("Sign out")
                    delete_button = gr.Button("Delete my account", variant="stop")
                    with gr.Column(visible=False) as delete_confirm:
                        html('<div class="sb-note">This removes your account and every month of data. It cannot be undone.</div>')
                        with gr.Row():
                            confirm_delete_button = gr.Button("Delete for good", variant="stop")
                            keep_button = gr.Button("Keep my account")

    # ---------- Wiring ----------

    limit_boxes = [limit_overall, limit_necessities, limit_discretionary, limit_travel]
    session_outputs = [user_state, budget_state, month_state, open_state, auth_view, app_view]
    target_boxes = [target_needs, target_wants, target_savings]
    signed_in_outputs = session_outputs + [greeting, display_name, *limit_boxes, savings_goal, *target_boxes, login_password, new_password]

    for trigger in (login_button.click, login_password.submit):
        trigger(sign_in, inputs=[login_username, login_password], outputs=signed_in_outputs)
    for trigger in (create_button.click, new_password.submit):
        trigger(create_account, inputs=[new_display_name, new_username, new_password], outputs=signed_in_outputs)

    month_state.change(lambda key: f'<div class="sb-title">{budget.month_label(key)}</div>', inputs=month_state, outputs=month_title)
    demo.load(lambda key: f'<div class="sb-title">{budget.month_label(key)}</div>', inputs=month_state, outputs=month_title)
    previous_month.click(lambda key: (budget.shift_month(key, -1), None), inputs=month_state, outputs=[month_state, open_state])
    next_month.click(lambda key: (budget.shift_month(key, 1), None), inputs=month_state, outputs=[month_state, open_state])

    save_limits_button.click(save_settings, inputs=[user_state, budget_state, *limit_boxes, savings_goal], outputs=budget_state)
    save_targets_button.click(save_targets, inputs=[user_state, budget_state, *target_boxes], outputs=[budget_state, *target_boxes])
    use_rule_button.click(use_50_30_20, inputs=[user_state, budget_state], outputs=[budget_state, *target_boxes])
    save_name_button.click(save_display_name, inputs=[user_state, display_name], outputs=[greeting, display_name])
    change_password_button.click(change_password, inputs=[user_state, current_password, changed_password], outputs=[current_password, changed_password])

    sign_out_button.click(sign_out, outputs=session_outputs + [greeting, login_password])
    delete_button.click(lambda: gr.update(visible=True), outputs=delete_confirm)
    keep_button.click(lambda: gr.update(visible=False), outputs=delete_confirm)
    confirm_delete_button.click(delete_account, inputs=user_state, outputs=session_outputs + [greeting, login_password, delete_confirm])


if __name__ == "__main__":
    demo.launch(theme=design.build_theme(), css=design.CSS, share="--share" in sys.argv)  # Colab needs the public link
