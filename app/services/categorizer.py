"""
Rule-based categorizer. Maps keywords in transaction descriptions to categories.
Fast, free, no API call needed for common merchants.
"""

RULES: list[tuple[list[str], str]] = [
    (["walmart", "target", "costco", "kroger", "whole foods", "trader joe", "safeway", "publix", "aldi"], "Groceries"),
    (["mcdonald", "starbucks", "chipotle", "subway", "dunkin", "doordash", "ubereats", "grubhub", "pizza", "burger", "taco", "chick-fil", "panera"], "Dining"),
    (["uber", "lyft", "parking", "toll", "gas", "shell", "bp ", "chevron", "exxon", "speedway", "sunoco"], "Transport"),
    (["netflix", "spotify", "hulu", "disney", "amazon prime", "apple.com/bill", "youtube", "hbo"], "Subscriptions"),
    (["amazon", "ebay", "etsy", "best buy", "apple store", "microsoft store"], "Shopping"),
    (["rent", "mortgage", "lease payment"], "Housing"),
    (["electric", "utility", "water bill", "gas bill", "pg&e", "con ed", "duke energy"], "Utilities"),
    (["at&t", "verizon", "t-mobile", "comcast", "xfinity", "spectrum"], "Phone/Internet"),
    (["cvs", "walgreens", "rite aid", "pharmacy", "hospital", "clinic", "doctor", "dental", "vision"], "Health"),
    (["gym", "planet fitness", "equinox", "ymca", "peloton"], "Fitness"),
    (["payroll", "direct deposit", "salary", "ach deposit", "zelle in", "venmo in"], "Income"),
    (["transfer", "zelle", "venmo", "paypal", "cash app"], "Transfer"),
    (["interest charge", "annual fee", "late fee", "service fee"], "Fees"),
    (["airline", "airbnb", "hotel", "marriott", "hilton", "expedia", "booking.com", "united", "delta", "southwest"], "Travel"),
    (["insurance", "geico", "progressive", "state farm", "allstate"], "Insurance"),
]


def categorize(description: str) -> str:
    desc = description.lower()
    for keywords, category in RULES:
        if any(kw in desc for kw in keywords):
            return category
    return "Uncategorized"
