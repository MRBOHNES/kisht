from datetime import date

import pytest

from app.csv_import import MissingColumns, parse_csv
from tests.world import csv_text, good_row

PINCODES = {"452010", "452001"}
TODAY = date(2026, 11, 9)


def parse(*rows):
    return parse_csv(csv_text(*rows), PINCODES, TODAY)


def fields_with_errors(result):
    return {(e.row, e.field) for e in result.errors}


def test_good_row_is_valid_and_blank_address_allowed():
    result = parse(good_row())
    assert len(result.valid) == 1 and not result.errors
    assert result.valid[0].address == ""


def test_missing_required_column_rejects_file():
    with pytest.raises(MissingColumns) as e:
        parse_csv("loan_id,dpd\nLN-1,3\n", PINCODES, TODAY)
    assert "pincode" in e.value.missing


def test_address_column_is_optional():
    text = "loan_id,business_name,business_type,phone,pincode,outstanding,emi,dpd,last_payment_date\n"
    text += "LN-1,Shop,dairy_shop,9876543210,452010,100000,9000,5,\n"
    assert len(parse_csv(text, PINCODES, TODAY).valid) == 1


def test_blank_last_payment_means_never_paid():
    result = parse(good_row(last=""))
    assert result.valid[0].last_payment_date is None


def test_errors_carry_row_number_and_fix_hint():
    result = parse(good_row(), good_row("LN-2", phone="123"))
    error = result.errors[0]
    assert (error.row, error.field, error.loan_id) == (3, "phone", "LN-2")
    assert error.fix


@pytest.mark.parametrize("override,field", [
    ({"loan_id": "XX-1"}, "loan_id"),
    ({"phone": "12345"}, "phone"),
    ({"pincode": "99999"}, "pincode"),
    ({"pincode": "999999"}, "pincode"),
    ({"outstanding": "abc"}, "outstanding"),
    ({"outstanding": "-5"}, "outstanding"),
    ({"emi": "0"}, "emi"),
    ({"dpd": "0"}, "dpd"),
    ({"dpd": "x"}, "dpd"),
    ({"last": "05/11/2026"}, "last_payment_date"),
    ({"last": "2026-12-01"}, "last_payment_date"),
    ({"name": ""}, "business_name"),
])
def test_invalid_field_is_reported(override, field):
    assert (2, field) in fields_with_errors(parse(good_row(**override)))


def test_duplicate_loan_id_flags_second_row():
    result = parse(good_row("LN-1"), good_row("LN-1"))
    assert fields_with_errors(result) == {(3, "loan_id")}
    assert len(result.valid) == 1


def test_phone_with_country_code_is_normalised():
    result = parse(good_row(phone="+91 98765-43210"))
    assert result.valid[0].phone == "9876543210"


def test_invalid_row_still_counts_as_seen():
    result = parse(good_row("LN-9", phone="bad"))
    assert "LN-9" in result.seen_ids and not result.valid


def test_invalid_rows_counted_once_per_row():
    result = parse(good_row(phone="bad", dpd="0"))
    assert len(result.errors) == 2 and result.invalid_rows == 1
