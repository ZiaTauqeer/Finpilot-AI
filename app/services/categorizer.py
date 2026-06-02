from __future__ import annotations

import re

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Groceries": [r"supermarket", r"mart", r"grocery", r"fresh", r"hyper"],
    "Food & Dining": [r"restaurant", r"cafe", r"pizza", r"burger", r"swiggy", r"zomato", r"food"],
    "Transport": [r"uber", r"ola", r"metro", r"fuel", r"petrol", r"diesel", r"taxi"],
    "Shopping": [r"amazon", r"flipkart", r"myntra", r"store", r"mall", r"purchase"],
    "Bills & Utilities": [r"electricity", r"water", r"internet", r"mobile", r"recharge", r"bill"],
    "Health": [r"pharmacy", r"hospital", r"clinic", r"medic", r"doctor"],
    "Entertainment": [r"netflix", r"prime", r"spotify", r"movie", r"cinema", r"bookmyshow"],
    "Investments": [r"mutual", r"sip", r"stocks", r"nps", r"ppf", r"investment"],
    "Cash Withdrawal": [r"atm", r"cash withdrawal"],
}

DEFAULT_CATEGORY = "Miscellaneous"


def categorize_message(message: str) -> str:
    text = message.lower()
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return category
    return DEFAULT_CATEGORY
