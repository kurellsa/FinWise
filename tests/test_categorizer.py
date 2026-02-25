"""Unit tests for services/categorizer.py — pure logic, no DB needed."""
import pytest
from services.categorizer import categorize


@pytest.mark.parametrize("description,expected", [
    ("WALMART SUPERCENTER",      "Groceries"),
    ("TRADER JOE'S #123",        "Groceries"),
    ("STARBUCKS #4567",          "Dining"),
    ("DOORDASH*CHIPOTLE",        "Dining"),
    ("NETFLIX.COM",              "Subscriptions"),
    ("SPOTIFY USA",              "Subscriptions"),
    ("SHELL OIL 12345",          "Transport"),
    ("UBER *TRIP",               "Transport"),
    ("DIRECT DEPOSIT PAYROLL",   "Income"),
    ("ACH DEPOSIT SALARY",       "Income"),
    ("CVS PHARMACY #999",        "Health"),
    ("ANNUAL FEE",               "Fees"),
    ("GEICO INSURANCE",          "Insurance"),
    ("SOUTHWEST AIRLINES",       "Travel"),
    ("PLANET FITNESS",           "Fitness"),
    ("AMAZON.COM AMZN",          "Shopping"),
    ("RANDOM MERCHANT XYZ",      "Uncategorized"),
])
def test_categorize(description: str, expected: str):
    assert categorize(description) == expected


def test_case_insensitive():
    """Keyword matching must be case-insensitive."""
    assert categorize("starbucks coffee shop") == "Dining"
    assert categorize("NETFLIX") == "Subscriptions"


def test_first_matching_rule_wins():
    """Amazon appears in both Shopping; payroll should map to Income not Transfer."""
    assert categorize("PAYROLL ZELLE TRANSFER") == "Income"
