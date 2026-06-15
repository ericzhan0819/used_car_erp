from used_car_erp.used_car_erp.services.taiwan_coa_catalog_service import (
    CORE_ENABLED_CODES,
    get_taiwan_coa_catalog_summary,
    load_taiwan_coa_catalog,
    validate_taiwan_coa_catalog,
)


def test_taiwan_coa_catalog_can_be_loaded():
    catalog = load_taiwan_coa_catalog()

    assert catalog
    assert all(row.get("source_year") == "113" for row in catalog)


def test_taiwan_coa_catalog_validation_has_no_fatal_error():
    result = validate_taiwan_coa_catalog()

    assert result["is_valid"]
    assert result["errors"] == []


def test_taiwan_coa_catalog_codes_are_unique():
    catalog = load_taiwan_coa_catalog()
    codes = [row["code"] for row in catalog]

    assert len(codes) == len(set(codes))


def test_core_used_car_codes_exist_and_are_enabled():
    catalog_by_code = {row["code"]: row for row in load_taiwan_coa_catalog()}

    missing_codes = CORE_ENABLED_CODES - set(catalog_by_code)
    assert missing_codes == set()
    assert all(catalog_by_code[code]["is_enabled_by_default"] == 1 for code in CORE_ENABLED_CODES)


def test_duplicate_official_names_remain_separate_codes():
    catalog_by_code = {row["code"]: row for row in load_taiwan_coa_catalog()}

    assert catalog_by_code["0100005"]["official_item_name"] == "營業成本"
    assert catalog_by_code["0300090"]["official_item_name"] == "營業成本"


def test_disabled_rows_have_disabled_reason():
    disabled_rows = [row for row in load_taiwan_coa_catalog() if row["is_enabled_by_default"] == 0]

    assert disabled_rows
    assert all(row.get("disabled_reason") for row in disabled_rows)


def test_manual_review_required_rows_are_counted():
    catalog = load_taiwan_coa_catalog()
    summary = get_taiwan_coa_catalog_summary()

    expected_count = sum(1 for row in catalog if row["manual_review_required"] == 1)
    assert summary["manual_review_required_count"] == expected_count
    assert expected_count > 0
