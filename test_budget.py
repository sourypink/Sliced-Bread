"""Tests for budget.py and storage.py. Run with: python -m pytest"""

from datetime import date

import pytest

import budget
import storage


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

def make_budget():
    user_budget = budget.empty_budget()
    for section, name, amount in [
        ("income", "Salary", "3000"), ("income", "Freelance", "200"),
        ("necessities", "Rent", "1200"), ("necessities", "Groceries", "380.50"),
        ("discretionary", "Movies", "40"), ("travel", "Flights", "300"),
    ]:
        budget.add_item(user_budget, "2026-10", section, name, amount)
    return user_budget


def test_totals_and_leftover():
    month = budget.get_month(make_budget(), "2026-10")
    assert budget.section_total(month, "income") == 320000
    assert budget.total_expenses(month) == 120000 + 38050 + 4000 + 30000
    assert budget.leftover(month) == 320000 - 192050


def test_leftover_goes_negative_when_overspent():
    user_budget = budget.empty_budget()
    budget.add_item(user_budget, "2026-10", "income", "Job", "100")
    budget.add_item(user_budget, "2026-10", "necessities", "Rent", "185")
    assert budget.leftover(budget.get_month(user_budget, "2026-10")) == -8500


def test_empty_month_has_zero_everything():
    month = budget.get_month(budget.empty_budget(), "2030-01")
    assert budget.leftover(month) == 0 and budget.total_expenses(month) == 0


def test_remove_item():
    user_budget = make_budget()
    budget.remove_item(user_budget, "2026-10", "income", 1)
    assert budget.section_total(budget.get_month(user_budget, "2026-10"), "income") == 300000
    with pytest.raises(IndexError):
        budget.remove_item(user_budget, "2026-10", "income", 5)


def test_add_item_rejects_unknown_section_and_bad_amount_without_changing_anything():
    user_budget = budget.empty_budget()
    with pytest.raises(ValueError):
        budget.add_item(user_budget, "2026-10", "investments", "Stocks", "10")
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
    (("50", "30", "20"), {"needs": 50, "wants": 30, "savings": 20}),
    (("60%", " 20 ", "20"), {"needs": 60, "wants": 20, "savings": 20}),
    (("", "", ""), {}),
    ((None, None, None), {}),
])
def test_parse_targets_accepts(typed, targets):
    assert budget.parse_targets(*typed) == targets


@pytest.mark.parametrize("typed, message", [
    (("50", "30", "10"), r"add up to 100% \(now 90%\)"),
    (("50", "", "20"), "Wants must be a whole number"),
    (("50.5", "29.5", "20"), "Needs must be a whole number"),
    (("150", "-30", "-20"), "Needs must be a whole number"),
])
def test_parse_targets_rejects(typed, message):
    with pytest.raises(ValueError, match=message):
        budget.parse_targets(*typed)


def test_target_meters_compare_spending_to_share_of_income():
    # Income $3,200; needs $1,580.50; wants $340; left $1,279.50.
    meters = budget.target_meters(budget.RULE_50_30_20, budget.get_month(make_budget(), "2026-10"))
    assert meters["needs"]["actual_percent"] == 49 and meters["needs"]["state"] == "warn"
    assert meters["needs"]["label"] == "Near limit, $19.50 left"
    assert meters["wants"]["actual_percent"] == 11 and meters["wants"]["state"] == "good"
    assert meters["savings"]["actual_percent"] == 40 and meters["savings"]["label"] == "On target"


def test_target_meters_flag_overspending_and_short_savings():
    user_budget = budget.empty_budget()
    budget.add_item(user_budget, "2026-10", "income", "Job", "1000")
    budget.add_item(user_budget, "2026-10", "necessities", "Rent", "600")
    budget.add_item(user_budget, "2026-10", "travel", "Trip", "300")
    meters = budget.target_meters(budget.RULE_50_30_20, budget.get_month(user_budget, "2026-10"))
    assert meters["needs"]["label"] == "Over by $100"
    assert meters["wants"]["state"] == "warn"
    assert meters["savings"]["state"] == "warn" and meters["savings"]["label"] == "$100 short"


def test_target_meters_empty_without_targets_or_income():
    month = budget.get_month(make_budget(), "2026-10")
    assert budget.target_meters({}, month) == {}
    assert budget.target_meters(budget.RULE_50_30_20, budget.empty_month()) == {}


# ---------- budget.py: history ----------

def test_month_history_is_oldest_first_with_empty_months_as_zeros():
    rows = budget.month_history(make_budget(), "2026-11", 3)
    assert [row["key"] for row in rows] == ["2026-09", "2026-10", "2026-11"]
    assert [row["label"] for row in rows] == ["Sep", "Oct", "Nov"]
    assert rows[0]["income"] == 0 and rows[0]["spent"] == 0 and rows[0]["left"] == 0
    october = rows[1]
    assert october["income"] == 320000 and october["spent"] == 192050 and october["left"] == 127950
    assert october["sections"] == {"necessities": 158050, "discretionary": 4000, "travel": 30000}


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


def test_fill_sample_months_only_fills_empty_earlier_months():
    user_budget = make_budget()  # October has real data
    assert budget.fill_sample_months(user_budget, "2026-11") == 4
    assert budget.get_month(user_budget, "2026-10")["income"][0]["name"] == "Salary"
    assert "2026-11" not in user_budget["months"]
    assert all(item["name"].endswith(budget.SAMPLE_TAG) for item in budget.get_month(user_budget, "2026-06")["income"])
    assert budget.fill_sample_months(user_budget, "2026-11") == 0
    assert budget.months_with_data(user_budget) == 5


# ---------- storage.py ----------

@pytest.fixture(autouse=True)
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))


@pytest.mark.parametrize("typed, key", [("Mark", "mark"), (" Mark  G ", "mark_g"), ("../../etc/x", "etc_x"), ("Ana-María", "ana-mar_a")])
def test_any_name_maps_to_a_safe_file_key(typed, key):
    assert storage.file_key(typed) == key


@pytest.mark.parametrize("typed, message", [("", "Enter your name"), ("   ", "Enter your name"), ("!!!", "letter or number"), ("x" * 31, "30 characters")])
def test_unusable_names_are_rejected(typed, message):
    with pytest.raises(ValueError, match=message):
        storage.file_key(typed)


def test_new_name_starts_with_an_empty_budget():
    assert storage.load_budget("nobody") == budget.empty_budget()


def test_budget_round_trips_through_a_file():
    user_budget = make_budget()
    user_budget["settings"]["savings_goal"] = 500000
    storage.save_budget("mark", user_budget)
    assert storage.load_budget("mark") == user_budget
    assert storage.load_budget("someone_else") == budget.empty_budget()


def test_delete_budget(tmp_path):
    storage.save_budget("mark", make_budget())
    storage.delete_budget("mark")
    assert not (tmp_path / "mark.json").exists()
    storage.delete_budget("mark")  # deleting twice is fine
