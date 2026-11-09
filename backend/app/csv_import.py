import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = [
    "loan_id", "business_name", "business_type", "phone", "pincode",
    "outstanding", "emi", "dpd", "last_payment_date",
]
OPTIONAL_COLUMNS = ["address"]

# match the database column sizes, so a long value is a row error rather than a failed import
MAX_LOAN_ID, MAX_NAME, MAX_TYPE = 20, 120, 40
MAX_AMOUNT = Decimal("9999999999.99")


class MissingColumns(Exception):
    def __init__(self, missing: list[str]):
        self.missing = missing


@dataclass
class RowError:
    row: int
    loan_id: str
    field: str
    message: str
    fix: str


@dataclass
class LoanRow:
    loan_id: str
    business_name: str
    business_type: str
    phone: str
    pincode: str
    outstanding: Decimal
    emi: Decimal
    dpd: int
    last_payment_date: date | None
    address: str


@dataclass
class ParseResult:
    total_rows: int = 0
    valid: list[LoanRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    # every loan_id present in the file, valid or not: a bad row must not cure its loan
    seen_ids: set[str] = field(default_factory=set)

    @property
    def invalid_rows(self) -> int:
        return len({e.row for e in self.errors})


def parse_csv(text: str, known_pincodes: set[str], today: date) -> ParseResult:
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise MissingColumns(missing)
    reader.fieldnames = headers

    result = ParseResult()
    first_row_of: dict[str, int] = {}
    for row_number, raw in enumerate(reader, start=2):
        cells = {k: (v or "").strip() for k, v in raw.items() if k}
        result.total_rows += 1
        loan_id = cells.get("loan_id", "")
        errors, row = validate_row(row_number, cells, known_pincodes, today)
        if loan_id:
            result.seen_ids.add(loan_id)
            if loan_id in first_row_of:
                errors.append(RowError(
                    row_number, loan_id, "loan_id", f"Same loan_id as row {first_row_of[loan_id]}",
                    "Keep one row per loan; delete the repeated row",
                ))
            else:
                first_row_of[loan_id] = row_number
        if errors:
            result.errors.extend(errors)
        else:
            result.valid.append(row)
    return result


def validate_row(n: int, c: dict, known_pincodes: set[str], today: date):
    loan_id = c.get("loan_id", "")
    errors: list[RowError] = []

    def fail(column: str, message: str, fix: str):
        errors.append(RowError(n, loan_id, column, message, fix))

    if not re.fullmatch(r"LN-\d+", loan_id) or len(loan_id) > MAX_LOAN_ID:
        fail("loan_id", f"'{loan_id}' is not a loan id", "Use the form LN-10293")
    if not c.get("business_name"):
        fail("business_name", "Business name is empty", "Fill in the borrower's business name")
    elif len(c["business_name"]) > MAX_NAME:
        fail("business_name", f"Business name is over {MAX_NAME} characters", "Shorten the business name")
    if not c.get("business_type"):
        fail("business_type", "Business type is empty", "Fill in a type such as fertiliser_shop")
    elif len(c["business_type"]) > MAX_TYPE:
        fail("business_type", f"Business type is over {MAX_TYPE} characters", "Use a short type such as fertiliser_shop")

    phone = re.sub(r"\D", "", c.get("phone", ""))
    if len(phone) == 12 and phone.startswith("91"):
        phone = phone[2:]
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        fail("phone", f"'{c.get('phone', '')}' is not a valid mobile number", "Use a 10-digit Indian mobile number")

    pincode = c.get("pincode", "")
    if not re.fullmatch(r"\d{6}", pincode):
        fail("pincode", f"'{pincode}' is not a 6-digit pincode", "Use the 6-digit pincode, e.g. 452010")
    elif pincode not in known_pincodes:
        fail("pincode", f"No branch serves pincode {pincode}", "Check the pincode, or ask your admin to add it to a branch")

    outstanding = parse_money(c.get("outstanding", ""))
    if outstanding is None or not 0 < outstanding <= MAX_AMOUNT:
        fail("outstanding", f"'{c.get('outstanding', '')}' is not a valid amount", "Use a plain number such as 640000")
    emi = parse_money(c.get("emi", ""))
    if emi is None or not 0 < emi <= MAX_AMOUNT:
        fail("emi", f"'{c.get('emi', '')}' is not a valid amount", "Use a plain number such as 53000")

    dpd = None
    if re.fullmatch(r"\d+", c.get("dpd", "")) and 1 <= int(c["dpd"]) <= 999:
        dpd = int(c["dpd"])
    else:
        fail("dpd", f"'{c.get('dpd', '')}' is not a valid days-past-due", "Use a whole number of days, 1 or more")

    last_paid = None
    raw_date = c.get("last_payment_date", "")
    if raw_date:
        try:
            last_paid = date.fromisoformat(raw_date)
            if last_paid > today:
                fail("last_payment_date", f"{raw_date} is in the future", "Use the date the last payment was received")
        except ValueError:
            fail("last_payment_date", f"'{raw_date}' is not a date", "Use YYYY-MM-DD, or leave blank if never paid")

    if errors:
        return errors, None
    return errors, LoanRow(
        loan_id=loan_id, business_name=c["business_name"],
        business_type=re.sub(r"\s+", "_", c["business_type"].lower()),
        phone=phone, pincode=pincode, outstanding=outstanding, emi=emi, dpd=dpd,
        last_payment_date=last_paid, address=c.get("address", ""),
    )


def parse_money(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw.replace(",", "").replace(" ", ""))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None
