"""Tests for budget.py, storage.py and the History zoom helpers. Run with: python -m pytest"""

from datetime import date

import pytest

import budget
import charts
import design
import storage

TARGETS_45_30_20_5 = {"needs": 45, "wants": 30, "investing": 20, "savings": 5}  # what the meter tests were written for


# ---------- budget.py: input validation ----------

@pytest.mark.parametrize("typed, cents", [
    ("12", 1200), ("12.5", 1250), ("12.50", 1250), ("$1,200", 120000), (" 3 ", 300), (".99", 99), (7, 700),
])
def test_parse_amount_accepts_normal_input(typed, cents):
    assert budget.parse_amount(typed) == cents


@pytest.mark.parametrize("typed, message", [
    ("", "Enter an amount"), (None, "Enter an amount"), ("abc", "must be a number"), ("1.2.3", "must be a number"),
    ("-5", "negative"), ("0", "more than"), ("0.00", "more than"), ("1.234", "2 decimal"),
    ("10000001", "too large"), (".", "must be a number"),
])
def test_parse_amount_rejects_bad_input(typed, message):
    with pytest.raises(ValueError, match=message):
        budget.parse_amount(typed)


def test_optional_amount_treats_blank_and_zero_as_unset():
    assert budget.parse_optional_amount("") == 0
    assert budget.parse_optional_amount("0.00") == 0
    assert budget.parse_optional_amount("1,800") == 180000


def test_clean_name_trims_and_rejects_blank_or_long():
    assert budget.clean_name("  Rent   and  water ") == "Rent and water"
    with pytest.raises(ValueError, match="Enter a name"):
        budget.clean_name("   ")
    with pytest.raises(ValueError, match="40 characters"):
        budget.clean_name("x" * 41)


@pytest.mark.parametrize("cents, shown", [(120000, "$1,200"), (1250, "$12.50"), (-8500, "-$85"), (0, "$0"), (5, "$0.05")])
def test_format_money(cents, shown):
    assert budget.format_money(cents) == shown


# ---------- budget.py: calculations ----------

def add_travel_and_emergency_fund(user_budget):
    """The two subcategories many tests use; users add them, they aren't presets."""
    budget.add_subcategory(user_budget, "Travel", "wants")
    budget.add_subcategory(user_budget, "Emergency fund", "savings")
    return user_budget


def make_budget():
    user_budget = add_travel_and_emergency_fund(budget.empty_budget())
    for section, name, amount in [
        ("income", "Salary", "3000"), ("income", "Freelance", "200"),
        ("necessities", "Rent", "1200"), ("necessities", "Groceries", "380.50"),
        ("discretionary", "Movies", "40"), ("travel", "Flights", "300"),
    ]:
        budget.add_item(user_budget, "2026-10", section, name, amount)
    return user_budget


def test_totals_and_leftover():
    user_budget = make_budget()
    month = budget.get_month(user_budget, "2026-10")
    assert budget.section_total(month, "income") == 320000
    assert budget.total_expenses(user_budget, month) == 120000 + 38050 + 4000 + 30000
    assert budget.leftover(user_budget, month) == 320000 - 192050


def test_leftover_goes_negative_when_overspent():
    user_budget = budget.empty_budget()
    budget.add_item(user_budget, "2026-10", "income", "Job", "100")
    budget.add_item(user_budget, "2026-10", "necessities", "Rent", "185")
    assert budget.leftover(user_budget, budget.get_month(user_budget, "2026-10")) == -8500


def test_empty_month_has_zero_everything():
    user_budget = budget.empty_budget()
    month = budget.get_month(user_budget, "2030-01")
    assert budget.leftover(user_budget, month) == 0 and budget.total_expenses(user_budget, month) == 0


def test_remove_item():
    user_budget = make_budget()
    budget.remove_item(user_budget, "2026-10", "income", 1)
    assert budget.section_total(budget.get_month(user_budget, "2026-10"), "income") == 300000
    with pytest.raises(IndexError):
        budget.remove_item(user_budget, "2026-10", "income", 5)


def test_add_item_rejects_unknown_section_and_bad_amount_without_changing_anything():
    user_budget = budget.empty_budget()
    with pytest.raises(ValueError):
        budget.add_item(user_budget, "2026-10", "nowhere", "Stocks", "10")
    with pytest.raises(ValueError):
        budget.add_item(user_budget, "2026-10", "income", "Job", "lots")
    assert user_budget["months"] == {}


@pytest.mark.parametrize("spent, limit, state, label", [
    (100, 0, "none", ""),
    (50000, 100000, "good", "$500 left"),
    (90000, 100000, "warn", "Near limit, $100 left"),
    (100000, 100000, "warn", "Near limit, $0 left"),
    (104500, 100000, "over", "Over by $45"),
])
def test_meter_states(spent, limit, state, label):
    result = budget.meter(spent, limit)
    assert result["state"] == state and result["label"] == label
    assert 0 <= result["fraction"] <= 1


def test_savings_progress_ignores_overspent_months():
    user_budget = make_budget()
    budget.add_item(user_budget, "2026-11", "income", "Job", "100")
    budget.add_item(user_budget, "2026-11", "travel", "Trip", "500")
    assert budget.savings_progress(user_budget) == 320000 - 192050


@pytest.mark.parametrize("key, steps, result", [("2026-10", 1, "2026-11"), ("2026-12", 1, "2027-01"), ("2026-01", -1, "2025-12")])
def test_shift_month(key, steps, result):
    assert budget.shift_month(key, steps) == result


def test_month_key_and_label():
    assert budget.month_key(date(2026, 3, 9)) == "2026-03"
    assert budget.month_label("2026-10") == "October 2026"


# ---------- budget.py: editing a line ----------

def test_update_item_replaces_name_and_amount():
    user_budget = make_budget()
    budget.update_item(user_budget, "2026-10", "necessities", 0, "Rent and water", "1,250")
    month = budget.get_month(user_budget, "2026-10")
    assert month["necessities"][0] == {"name": "Rent and water", "amount": 125000}
    assert budget.section_total(month, "necessities") == 125000 + 38050


def test_update_item_rejects_bad_input_without_changing_anything():
    user_budget = make_budget()
    with pytest.raises(ValueError):
        budget.update_item(user_budget, "2026-10", "necessities", 0, "Rent", "-5")
    with pytest.raises(IndexError):
        budget.update_item(user_budget, "2026-10", "necessities", 9, "Rent", "5")
    assert budget.get_month(user_budget, "2026-10")["necessities"][0] == {"name": "Rent", "amount": 120000}


# ---------- budget.py: percentage targets ----------

@pytest.mark.parametrize("typed, targets", [
    (("50", "30", "10", "10"), {"needs": 50, "wants": 30, "investing": 10, "savings": 10}),
    (("60%", " 20 ", "15", "5"), {"needs": 60, "wants": 20, "investing": 15, "savings": 5}),
    (("", "", "", ""), {}),
    ((None, None, None, None), {}),
])
def test_parse_targets_accepts(typed, targets):
    assert budget.parse_targets(*typed) == targets


@pytest.mark.parametrize("typed, message", [
    (("50", "30", "10", "0"), r"add up to 100% \(now 90%\)"),
    (("50", "", "10", "10"), "Wants must be a whole number"),
    (("50.5", "29.5", "10", "10"), "Needs must be a whole number"),
    (("150", "-30", "-10", "-10"), "Needs must be a whole number"),
    (("50", "30", "x", "10"), "Investing must be a whole number"),
])
def test_parse_targets_rejects(typed, message):
    with pytest.raises(ValueError, match=message):
        budget.parse_targets(*typed)


def test_target_meters_compare_spending_to_share_of_income():
    # Income $3,200; needs $1,580.50; wants $340; nothing invested; saved $1,279.50.
    user_budget = make_budget()
    meters = budget.target_meters(user_budget, TARGETS_45_30_20_5, budget.get_month(user_budget, "2026-10"))
    assert meters["needs"]["actual_percent"] == 49 and meters["needs"]["state"] == "over"
    assert meters["needs"]["label"] == "Over by $140.50"
    assert meters["wants"]["actual_percent"] == 11 and meters["wants"]["label"] == "$620 left"
    assert meters["investing"]["actual_percent"] == 0 and meters["investing"]["label"] == "$640 short"
    assert meters["savings"]["actual_percent"] == 40 and meters["savings"]["label"] == "On target"


def test_target_meters_flag_overspending_and_short_minimums():
    user_budget = add_travel_and_emergency_fund(budget.empty_budget())
    budget.add_item(user_budget, "2026-10", "income", "Job", "1000")
    budget.add_item(user_budget, "2026-10", "necessities", "Rent", "600")
    budget.add_item(user_budget, "2026-10", "travel", "Trip", "300")
    budget.add_item(user_budget, "2026-10", "investments", "Roth IRA", "60")
    meters = budget.target_meters(user_budget, TARGETS_45_30_20_5, budget.get_month(user_budget, "2026-10"))
    assert meters["needs"]["label"] == "Over by $150"
    assert meters["wants"]["state"] == "warn"
    assert meters["investing"]["state"] == "warn" and meters["investing"]["label"] == "$140 short"
    assert meters["savings"]["state"] == "warn" and meters["savings"]["label"] == "$10 short"


def test_target_meters_empty_without_targets_or_income():
    user_budget = make_budget()
    month = budget.get_month(user_budget, "2026-10")
    assert budget.target_meters(user_budget, {}, month) == {}
    assert budget.target_meters(user_budget, TARGETS_45_30_20_5, budget.get_month(user_budget, "2030-01")) == {}


def test_targets_saved_with_three_shares_count_as_off():
    old_style = {"needs": 50, "wants": 30, "savings": 20}
    user_budget = make_budget()
    assert budget.target_meters(user_budget, old_style, budget.get_month(user_budget, "2026-10")) == {}


# ---------- budget.py: investments and savings ----------

def test_investing_comes_out_before_savings():
    user_budget = make_budget()
    budget.add_item(user_budget, "2026-10", "investments", "Roth IRA", "500")
    month = budget.get_month(user_budget, "2026-10")
    assert budget.total_invested(user_budget, month) == 50000
    assert budget.total_expenses(user_budget, month) == 192050  # spending only, so limits ignore investing
    assert budget.leftover(user_budget, month) == 320000 - 192050 - 50000


def test_investment_lines_are_plain_lines():
    user_budget = budget.empty_budget()
    assert budget.add_item(user_budget, "2026-10", "investments", "Roth IRA", "100") == {"name": "Roth IRA", "amount": 10000}


def test_budgets_saved_before_investments_existed_still_work():
    old_month = {"income": [{"name": "Job", "amount": 100000}], "necessities": [], "discretionary": [], "travel": []}
    user_budget = {**budget.empty_budget(), "months": {"2026-10": old_month}}
    assert budget.get_month(user_budget, "2026-10")["investments"] == []
    assert budget.leftover(user_budget, budget.get_month(user_budget, "2026-10")) == 100000
    budget.add_item(user_budget, "2026-10", "investments", "Roth IRA", "100")
    assert budget.total_invested(user_budget, budget.get_month(user_budget, "2026-10")) == 10000


# ---------- budget.py: subcategories ----------

def test_new_budgets_start_with_the_presets_in_their_categories():
    subs = budget.subcategories(budget.empty_budget())
    assert [(sub["key"], sub["category"]) for sub in subs] == [
        ("necessities", "needs"), ("discretionary", "wants"), ("investments", "investing"),
    ]


def test_old_budgets_keep_a_retired_preset_that_holds_lines():
    user_budget = budget.empty_budget()
    assert "travel" not in budget.section_keys(user_budget)
    user_budget["months"]["2026-10"] = {"travel": [{"name": "Flights", "amount": 30000}]}
    assert "travel" in budget.section_keys(user_budget) and "emergency_fund" not in budget.section_keys(user_budget)
    assert budget.category_total(user_budget, budget.get_month(user_budget, "2026-10"), "wants") == 30000


def test_budgets_saved_before_a_new_preset_get_it():
    user_budget = make_budget()
    pets = budget.add_subcategory(user_budget, "Pets", "wants")
    stored = user_budget["settings"]["subcategories"]
    stored.remove(next(sub for sub in stored if sub["key"] == "investments"))
    assert [sub["key"] for sub in budget.subcategories(user_budget)][-2:] == ["pets", "investments"]
    budget.rename_subcategory(user_budget, "investments", "Stocks")
    assert stored[-1] == {"key": "investments", "name": "Stocks", "category": "investing"} and pets in stored


def test_added_subcategory_counts_toward_its_category():
    user_budget = make_budget()
    pets = budget.add_subcategory(user_budget, "  Pets ", "wants")
    assert pets == {"key": "pets", "name": "Pets", "category": "wants"}
    budget.add_item(user_budget, "2026-10", "pets", "Vet", "60")
    month = budget.get_month(user_budget, "2026-10")
    assert budget.category_total(user_budget, month, "wants") == 4000 + 30000 + 6000
    assert budget.total_expenses(user_budget, month) == 192050 + 6000


def test_subcategory_names_must_be_unique_and_not_a_category():
    user_budget = add_travel_and_emergency_fund(budget.empty_budget())
    for name in ("travel", "Needs", "Income", "all spending"):
        with pytest.raises(ValueError, match="You already have"):
            budget.add_subcategory(user_budget, name, "wants")
    with pytest.raises(ValueError, match="Pick a category"):
        budget.add_subcategory(user_budget, "Pets", "fun")


def test_subcategory_keys_never_clash():
    user_budget = add_travel_and_emergency_fund(budget.empty_budget())
    budget.rename_subcategory(user_budget, "travel", "Trips")
    assert budget.add_subcategory(user_budget, "Travel", "wants")["key"] == "travel_2"
    assert budget.add_subcategory(user_budget, "!!!", "needs")["key"] == "subcategory"


def test_custom_subcategories_are_capped():
    user_budget = budget.empty_budget()
    for number in range(budget.MAX_CUSTOM_SUBCATEGORIES):
        budget.add_subcategory(user_budget, f"Extra {number}", "wants")
    with pytest.raises(ValueError, match="up to"):
        budget.add_subcategory(user_budget, "One more", "wants")


def test_moving_a_subcategory_moves_its_money_between_categories():
    user_budget = make_budget()
    budget.move_subcategory(user_budget, "travel", "needs")
    month = budget.get_month(user_budget, "2026-10")
    assert budget.category_total(user_budget, month, "needs") == 158050 + 30000
    assert budget.category_total(user_budget, month, "wants") == 4000
    assert [sub["key"] for sub in budget.subcategories_in(user_budget, "needs")] == ["necessities", "travel"]


def test_rename_keeps_the_lines():
    user_budget = make_budget()
    budget.rename_subcategory(user_budget, "travel", "Trips")
    assert budget.subcategories_in(user_budget, "wants")[1]["name"] == "Trips"
    assert budget.get_month(user_budget, "2026-10")["travel"][0]["name"] == "Flights"
    with pytest.raises(ValueError, match="You already have"):
        budget.rename_subcategory(user_budget, "travel", "discretionary")
    budget.rename_subcategory(user_budget, "travel", "TRIPS")  # its own name in other capitals is fine


def test_remove_refuses_subcategories_with_items():
    user_budget = make_budget()
    with pytest.raises(ValueError, match="has items in 1 month"):
        budget.remove_subcategory(user_budget, "travel")  # a preset, but it holds Flights
    budget.add_subcategory(user_budget, "Pets", "wants")
    budget.add_item(user_budget, "2026-10", "pets", "Vet", "60")
    with pytest.raises(ValueError, match="has items in 1 month. Delete them first"):
        budget.remove_subcategory(user_budget, "pets")
    budget.remove_item(user_budget, "2026-10", "pets", 0)
    budget.remove_subcategory(user_budget, "pets")
    assert "pets" not in budget.section_keys(user_budget)
    assert "pets" not in user_budget["months"]["2026-10"]


def test_a_removed_preset_stays_removed():
    user_budget = make_budget()
    budget.remove_subcategory(user_budget, "investments")
    assert "investments" not in budget.section_keys(user_budget)
    budget.rename_subcategory(user_budget, "travel", "Trips")  # writes the list out again; the preset must not return
    assert "investments" not in budget.section_keys(user_budget)


def test_removing_investments_leaves_sample_months_working():
    user_budget = budget.empty_budget()
    budget.remove_subcategory(user_budget, "investments")
    assert budget.fill_sample_months(user_budget, "2026-11") == 5
    assert budget.month_history(user_budget, "2026-10", 1)[0]["invested"] == 0


# ---------- budget.py: plan presets and the monthly limit ----------

def test_every_plan_preset_covers_all_four_categories_and_makes_100():
    for preset in budget.PLAN_PRESETS:
        assert set(preset["targets"]) == set(budget.CATEGORIES)
        assert sum(preset["targets"].values()) == budget.PERCENT_WHOLE
        assert budget.parse_targets(*(str(preset["targets"][category]) for category in budget.CATEGORIES)) == preset["targets"]


def test_category_limits_are_the_monthly_limit_times_each_target():
    settings = {"limits": {"overall": 300000}, "targets": {"needs": 50, "wants": 30, "investing": 15, "savings": 5}}
    assert budget.category_limits(settings) == {"needs": 150000, "wants": 90000, "investing": 45000, "savings": 15000}
    settings["limits"]["overall"] = 99999  # $999.99: shares round down to the cent
    assert budget.category_limits(settings)["savings"] == 4999


def test_category_limits_are_off_without_a_limit_or_targets():
    assert budget.category_limits({"limits": {"overall": 0}, "targets": TARGETS_45_30_20_5}) == {}
    assert budget.category_limits({"limits": {"overall": 300000}, "targets": {}}) == {}
    assert budget.category_limits(budget.empty_budget()["settings"]) == {}


def test_plan_amounts_follow_whatever_is_typed():
    assert budget.plan_amounts("$3,000", ["50", "30", "", "x"]) == {"needs": 150000, "wants": 90000}
    assert budget.plan_amounts("", ["50", "30", "15", "5"]) == {}
    assert budget.plan_amounts("abc", ["50", "30", "15", "5"]) == {}


def test_donut_has_a_segment_per_category_with_money():
    amounts = {"needs": 120000, "wants": 30000, "investing": 0, "savings": 50000}
    ring = design.donut_svg(amounts, 200000)
    assert ring.count("<circle") == 3 and "$2,000" in ring and "Needs $1,200 (60%)" in ring
    empty = design.donut_svg(dict.fromkeys(amounts, 0), 0)
    assert empty.count("<circle") == 1 and design.LINE in empty


def test_savings_subcategory_is_set_aside_not_left_over():
    user_budget = make_budget()
    budget.add_item(user_budget, "2026-10", "emergency_fund", "Transfer", "300")
    month = budget.get_month(user_budget, "2026-10")
    assert budget.leftover(user_budget, month) == 127950 - 30000
    assert budget.saved(user_budget, month) == 127950
    assert budget.savings_progress(user_budget) == 127950
    meters = budget.target_meters(user_budget, TARGETS_45_30_20_5, month)
    assert meters["savings"]["actual_percent"] == 40


@pytest.mark.parametrize("texts, auto_key, edited, result, new_auto", [
    (["50", "30", "10", ""], None, "investing", ["50", "30", "10", "10"], "savings"),  # three typed: fourth fills
    (["50", "", "10", ""], None, "investing", ["50", "", "10", ""], None),  # two blanks: wait
    (["60", "30", "10", "10"], "savings", "needs", ["60", "30", "10", "0"], "savings"),  # keeps in step
    (["70", "30", "10", "10"], "savings", "needs", ["70", "30", "10", ""], "savings"),  # over 100: blank, not negative
    (["50", "30", "10", "15"], "savings", "savings", ["50", "30", "10", "15"], None),  # typing in it hands it back
    (["50", "30", "10", "10"], "savings", "savings", ["50", "30", "10", "10"], "savings"),  # its own update
    (["50", "x", "10", ""], None, "wants", ["50", "x", "10", ""], None),    (["50", "30", "10", ""], None, "savings", ["50", "30", "10", ""], None),  # just cleared it: leave it alone
])
def test_complete_targets(texts, auto_key, edited, result, new_auto):
    assert budget.complete_targets(texts, auto_key, edited) == (result, new_auto)


# ---------- budget.py: history ----------

def test_month_history_is_oldest_first_with_empty_months_as_zeros():
    rows = budget.month_history(make_budget(), "2026-11", 3)
    assert [row["key"] for row in rows] == ["2026-09", "2026-10", "2026-11"]
    assert [row["label"] for row in rows] == ["Sep", "Oct", "Nov"]
    assert rows[0]["income"] == 0 and rows[0]["spent"] == 0 and rows[0]["left"] == 0
    october = rows[1]
    assert october["income"] == 320000 and october["spent"] == 192050 and october["left"] == 127950
    assert october["subcategories"] == {"necessities": 158050, "discretionary": 4000, "travel": 30000, "investments": 0,
                                     "emergency_fund": 0}
    assert october["categories"] == {"needs": 158050, "wants": 34000, "investing": 0, "savings": 0}
    assert october["invested"] == 0 and october["saved"] == 127950


def test_month_history_crosses_the_year_boundary():
    assert [row["key"] for row in budget.month_history(budget.empty_budget(), "2027-01", 3)] == ["2026-11", "2026-12", "2027-01"]


@pytest.mark.parametrize("choice, count", [("6 months", 6), ("12 months", 12)])
def test_history_range_fixed_windows_end_today(choice, count):
    assert budget.history_range(make_budget(), choice, "2026-11") == ("2026-11", count)


def test_history_range_all_starts_at_the_first_month_with_data():
    assert budget.history_range(make_budget(), "All", "2026-11") == ("2026-11", 2)
    assert budget.history_range(budget.empty_budget(), "All", "2026-11") == ("2026-11", 1)


def test_history_range_all_is_capped():
    user_budget = budget.empty_budget()
    budget.add_item(user_budget, "2020-01", "income", "Job", "100")
    assert budget.history_range(user_budget, "All", "2026-11") == ("2026-11", budget.MAX_HISTORY_MONTHS)


def test_top_items_largest_first_and_limited():
    user_budget = make_budget()
    budget.add_item(user_budget, "2026-09", "necessities", "Car repair", "900")
    items = budget.top_items(user_budget, ["2026-09", "2026-10"], "necessities", limit=2)
    assert items == [("Rent", "2026-10", 120000), ("Car repair", "2026-09", 90000)]


def test_section_lines_merges_same_label_and_keeps_empty_months():
    user_budget = budget.empty_budget()
    budget.add_item(user_budget, "2026-09", "necessities", "Rent", "1000")
    budget.add_item(user_budget, "2026-09", "necessities", "Rent", "200")
    budget.add_item(user_budget, "2026-09", "investments", "Index fund", "50")
    assert budget.section_lines(user_budget, ["2026-08", "2026-09"], "necessities") == {"2026-08": {}, "2026-09": {"Rent": 120000}}
    assert budget.section_lines(user_budget, ["2026-09"], "investments") == {"2026-09": {"Index fund": 5000}}


def test_shades_run_darkest_to_lightest():
    colors = design.shades("#2A78D6", 4)
    assert len(colors) == 4 and all(len(color) == 7 and color.startswith("#") for color in colors)
    brightness = [sum(int(color[i:i + 2], 16) for i in (1, 3, 5)) for color in colors]
    assert brightness == sorted(brightness) and colors[0] != colors[-1]
    assert design.shades("#2A78D6", 1) == ["#2A78D6"]


def test_zoom_series_ranks_by_range_total_and_groups_the_rest():
    lines = {"2026-09": {f"Line {n}": n * 100 for n in range(1, 8)}, "2026-10": {"Line 1": 10_000}}
    names = [name for name, _ in charts.zoom_series(lines, "#2A78D6")]
    assert names == ["Line 1", "Line 7", "Line 6", "Line 5", "Line 4", charts.OTHER_LABEL]
    assert charts.month_amounts(lines["2026-09"], charts.zoom_series(lines, "#2A78D6"))[-1] == 300 + 200


def test_chart_views_drill_from_categories_to_subcategories_to_items():
    user_budget = make_budget()
    budget.add_item(user_budget, "2026-10", "emergency_fund", "Transfer", "100")
    rows = budget.month_history(user_budget, "2026-10", 2)
    everything = charts.chart_view(user_budget, rows, "all")
    assert [name for name, *_ in everything["series"]] == ["Needs", "Wants", "Investing", "Savings"]
    assert charts.view_totals(everything, rows) == [0, 192050 + 10000]
    wants = charts.chart_view(user_budget, rows, "category:wants")
    assert [(name, zoom) for name, _, zoom, _ in wants["series"]] == [("Discretionary", "Discretionary"), ("Travel", "Travel")]
    savings = charts.chart_view(user_budget, rows, "category:savings")
    assert savings["series"][-1][0] == charts.LEFT_OVER_LABEL and savings["series"][-1][3] == [0, 127950 - 10000]
    travel = charts.chart_view(user_budget, rows, "sub:travel")
    assert travel["back"] == "Wants" and travel["series"][0][0] == "Flights" and travel["series"][0][3] == [0, 30000]
    for view in (everything, wants, savings, travel):
        assert "by month" in charts.history_chart(rows, view) or view is everything


def test_subcategory_colors_are_shades_of_their_category():
    user_budget = add_travel_and_emergency_fund(budget.empty_budget())
    colors = design.subcategory_colors(user_budget)
    assert colors["necessities"] == design.CATEGORY_COLORS["needs"]  # alone in its category: the colour itself
    assert colors["discretionary"] != colors["travel"]
    assert design.marker("wants").count("Wants") == 1


def test_fill_sample_months_only_fills_empty_earlier_months():
    user_budget = make_budget()  # October has real data
    assert budget.fill_sample_months(user_budget, "2026-11") == 4
    assert budget.get_month(user_budget, "2026-10")["income"][0]["name"] == "Salary"
    assert "2026-11" not in user_budget["months"]
    assert all(item["name"].endswith(budget.SAMPLE_TAG) for item in budget.get_month(user_budget, "2026-06")["income"])
    assert budget.fill_sample_months(user_budget, "2026-11") == 0
    assert budget.months_with_data(user_budget) == 5
    assert budget.month_history(user_budget, "2026-07", 1)[0]["invested"] == 40000


# ---------- storage.py ----------

@pytest.fixture(autouse=True)
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))


@pytest.mark.parametrize("typed, message", [("", "Enter your name"), ("   ", "Enter your name"), ("x" * 31, "30 characters")])
def test_unusable_names_are_rejected(typed, message):
    with pytest.raises(ValueError, match=message):
        storage.clean_name(typed)


def test_budget_round_trips_through_a_file():
    user_budget = make_budget()
    user_budget["settings"]["savings_goal"] = 500000
    storage.save_budget("mark@example.com", user_budget)
    assert storage.load_budget("mark@example.com") == user_budget
    assert not storage.account_exists("someone@example.com")


def test_delete_budget(tmp_path):
    storage.save_budget("mark@example.com", make_budget())
    storage.delete_budget("mark@example.com")
    assert not (tmp_path / "mark@example.com.json").exists()
    storage.delete_budget("mark@example.com")  # deleting twice is fine


def test_create_account_then_log_in_with_its_email():
    key, user_budget = storage.create_account(" Mark  G ", " Mark@Example.com ", "correct horse", "correct horse")
    assert key == "mark@example.com"
    assert user_budget["account"]["name"] == "Mark G" and user_budget["account"]["email"] == key
    assert "correct horse" not in str(user_budget["account"])
    assert storage.log_in("MARK@example.com", "correct horse") == (key, user_budget)


@pytest.mark.parametrize("email, password", [("mark@example.com", "wrong password"), ("nobody@example.com", "correct horse")])
def test_log_in_refuses_a_wrong_password_or_unknown_email_alike(email, password):
    storage.create_account("Mark", "mark@example.com", "correct horse", "correct horse")
    with pytest.raises(ValueError, match="email and password don't match"):
        storage.log_in(email, password)


def test_create_account_refuses_a_taken_email():
    storage.create_account("Mark", "mark@example.com", "correct horse", "correct horse")
    with pytest.raises(ValueError, match="already exists"):
        storage.create_account("Someone else", "mark@example.com", "other password", "other password")


@pytest.mark.parametrize("password, confirm, message", [("short", "short", "at least 8"), ("correct horse", "correct hose", "don't match")])
def test_create_account_refuses_bad_passwords(password, confirm, message):
    with pytest.raises(ValueError, match=message):
        storage.create_account("Mark", "mark@example.com", password, confirm)
    assert not storage.account_exists("mark@example.com")  # nothing saved


def test_same_password_gets_a_different_salt():
    assert storage.hash_password("same one") != storage.hash_password("same one")


@pytest.mark.parametrize("typed, email", [("  A@b.co ", "a@b.co"), ("first.last+tag@mail.example.org", "first.last+tag@mail.example.org")])
def test_clean_email_accepts(typed, email):
    assert storage.clean_email(typed) == email


@pytest.mark.parametrize("typed", ["nope", "a@b", "a b@c.d", "../x@b.co", "a@b/c.co", "x" * 250 + "@b.co"])
def test_clean_email_rejects(typed):
    with pytest.raises(ValueError, match="name@example.com"):
        storage.clean_email(typed)


def test_clean_email_requires_one():
    with pytest.raises(ValueError, match="Enter your email"):
        storage.clean_email("  ")


def test_rename_budget_refuses_a_taken_email(tmp_path):
    storage.save_budget("mark@example.com", make_budget())
    storage.save_budget("ana@example.com", budget.empty_budget())
    with pytest.raises(ValueError, match="already uses that email"):
        storage.rename_budget("mark@example.com", "ana@example.com")
    storage.rename_budget("mark@example.com", "marcus@example.com")
    assert not storage.account_exists("mark@example.com") and storage.load_budget("marcus@example.com") == make_budget()


def test_limit_meters_redden_as_they_fill():
    assert design.limit_color(0) == design.ACCENT
    assert design.limit_color(budget.WARN_AT) == design.WARN
    assert design.limit_color(1.0) == design.limit_color(1.5) == design.OVER
    halfway = design.limit_color(0.5)
    assert halfway not in (design.ACCENT, design.WARN, design.OVER)
