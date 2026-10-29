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


# ---------- storage.py ----------

@pytest.fixture(autouse=True)
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))


def test_create_account_and_sign_in():
    assert storage.create_account(" Mark_G ", "secret1", "Mark") == "mark_g"
    assert storage.sign_in("MARK_G", "secret1") == "mark_g"
    assert storage.get_display_name("mark_g") == "Mark"


@pytest.mark.parametrize("username, password, message", [
    ("ab", "secret1", "3-20"), ("has space", "secret1", "3-20"), ("../evil", "secret1", "3-20"), ("okname", "123", "at least 6"),
])
def test_create_account_rejects_bad_input(username, password, message):
    with pytest.raises(ValueError, match=message):
        storage.create_account(username, password)


def test_duplicate_username_rejected():
    storage.create_account("mark", "secret1")
    with pytest.raises(ValueError, match="taken"):
        storage.create_account("MARK", "secret2")


@pytest.mark.parametrize("username, password", [("mark", "wrong12"), ("nobody", "secret1"), ("", "")])
def test_sign_in_fails_with_one_message(username, password):
    storage.create_account("mark", "secret1")
    with pytest.raises(ValueError, match="Wrong username or password"):
        storage.sign_in(username, password)


def test_password_is_not_stored_in_plain_text(tmp_path):
    storage.create_account("mark", "secret1")
    assert "secret1" not in (tmp_path / "users.json").read_text()


def test_budget_round_trips_through_a_file():
    storage.create_account("mark", "secret1")
    user_budget = make_budget()
    user_budget["settings"]["savings_goal"] = 500000
    storage.save_budget("mark", user_budget)
    assert storage.load_budget("mark") == user_budget


def test_change_password():
    storage.create_account("mark", "secret1")
    with pytest.raises(ValueError, match="Wrong"):
        storage.change_password("mark", "nope123", "newpass1")
    storage.change_password("mark", "secret1", "newpass1")
    assert storage.sign_in("mark", "newpass1") == "mark"
    with pytest.raises(ValueError):
        storage.sign_in("mark", "secret1")


def test_delete_account_removes_user_and_budget(tmp_path):
    storage.create_account("mark", "secret1")
    storage.delete_account("mark")
    assert not (tmp_path / "mark.json").exists()
    with pytest.raises(ValueError):
        storage.sign_in("mark", "secret1")
