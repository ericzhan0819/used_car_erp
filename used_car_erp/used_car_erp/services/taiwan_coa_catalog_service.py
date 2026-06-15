import json
from collections import Counter
from pathlib import Path


SOURCE_YEAR = "113"

ALLOWED_ROOT_TYPES = {"Asset", "Liability", "Equity", "Income", "Expense"}
ALLOWED_REPORT_TYPES = {"Balance Sheet", "Profit and Loss", "Cost Statement", "Other"}
BINARY_FIELDS = {
    "is_group",
    "is_enabled_by_default",
    "is_system_required",
    "manual_review_required",
}

CORE_ENABLED_CODES = {
    "0201111",
    "0201112",
    "0201123",
    "0201129",
    "0201130",
    "0201131",
    "0201144",
    "0201145",
    "0202121",
    "0202130",
    "0202132",
    "0202134",
    "0202136",
    "0202137",
    "0202138",
    "0100001",
    "0100004",
    "0100005",
    "0300090",
    "0100010",
    "0100011",
    "0100012",
    "0100013",
    "0100014",
    "0100015",
    "0100016",
    "0100017",
    "0100018",
    "0100019",
    "0100020",
    "0100022",
    "0100024",
    "0100027",
    "0100028",
    "0100030",
    "0100031",
    "0100032",
}

REQUIRED_REVIEW_CODES = {
    "0100005",
    "0300090",
    "0202134",
    "0201144",
    "0201145",
    "0202136",
    "0201123",
    "0201131",
}


def _catalog_path():
    return Path(__file__).resolve().parents[2] / "data" / "taiwan_coa_113_full.json"


def load_taiwan_coa_catalog():
    with _catalog_path().open(encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


def get_taiwan_coa_catalog_summary():
    catalog = load_taiwan_coa_catalog()
    codes = [row.get("code") for row in catalog if row.get("source_year") == SOURCE_YEAR]
    duplicate_codes = sorted(code for code, count in Counter(codes).items() if code and count > 1)
    catalog_codes = set(codes)

    return {
        "source_year": SOURCE_YEAR,
        "total_count": len(catalog),
        "enabled_count": sum(1 for row in catalog if row.get("is_enabled_by_default") == 1),
        "disabled_count": sum(1 for row in catalog if row.get("is_enabled_by_default") == 0),
        "group_count": sum(1 for row in catalog if row.get("is_group") == 1),
        "ledger_count": sum(1 for row in catalog if row.get("is_group") == 0),
        "manual_review_required_count": sum(
            1 for row in catalog if row.get("manual_review_required") == 1
        ),
        "duplicate_codes": duplicate_codes,
        "missing_core_codes": sorted(CORE_ENABLED_CODES - catalog_codes),
    }


def validate_taiwan_coa_catalog():
    catalog = load_taiwan_coa_catalog()
    errors = []
    warnings = []
    codes = []

    for row_number, row in enumerate(catalog, start=1):
        code = row.get("code")
        codes.append(code)

        if not code:
            errors.append(f"row {row_number}: code is required")
        if row.get("source_year") != SOURCE_YEAR:
            errors.append(f"{code or row_number}: source_year must be {SOURCE_YEAR}")
        if not row.get("official_item_name"):
            errors.append(f"{code or row_number}: official_item_name is required")
        if not row.get("account_number"):
            errors.append(f"{code or row_number}: account_number is required")
        if row.get("root_type") not in ALLOWED_ROOT_TYPES:
            errors.append(f"{code or row_number}: root_type is invalid")
        if row.get("report_type") not in ALLOWED_REPORT_TYPES:
            errors.append(f"{code or row_number}: report_type is invalid")

        for fieldname in BINARY_FIELDS:
            if row.get(fieldname) not in {0, 1}:
                errors.append(f"{code or row_number}: {fieldname} must be 0 or 1")

        if row.get("is_enabled_by_default") == 0 and not row.get("disabled_reason"):
            errors.append(f"{code or row_number}: disabled_reason is required")
        if code in CORE_ENABLED_CODES and row.get("is_enabled_by_default") != 1:
            errors.append(f"{code}: core used car account must be enabled by default")

    duplicate_codes = sorted(code for code, count in Counter(codes).items() if code and count > 1)
    if duplicate_codes:
        errors.append(f"duplicate code values: {', '.join(duplicate_codes)}")

    catalog_codes = {code for code in codes if code}
    missing_core_codes = sorted(CORE_ENABLED_CODES - catalog_codes)
    if missing_core_codes:
        errors.append(f"missing core codes: {', '.join(missing_core_codes)}")

    missing_review_codes = sorted(REQUIRED_REVIEW_CODES - catalog_codes)
    if missing_review_codes:
        errors.append(f"missing required review codes: {', '.join(missing_review_codes)}")
    if not {"0100005", "0300090"}.issubset(catalog_codes):
        errors.append("0100005 and 0300090 must both exist and must not be merged by name")

    return {
        "source_year": SOURCE_YEAR,
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": get_taiwan_coa_catalog_summary(),
    }
