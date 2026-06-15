from used_car_erp.used_car_erp.services.taiwan_coa_catalog_service import (
    CORE_ENABLED_CODES,
    load_taiwan_coa_catalog,
)
from used_car_erp.used_car_erp.services.taiwan_coa_importer_export_service import (
    DISABLED_SUPPORTED_BY_IMPORTER,
    generate_taiwan_coa_importer_files,
    generate_taiwan_coa_importer_preview,
    get_taiwan_coa_importer_export_summary,
    validate_taiwan_coa_importer_export,
)


def test_taiwan_coa_importer_export_summary_can_be_loaded():
    summary = get_taiwan_coa_importer_export_summary()

    assert summary["source_year"] == "113"
    assert summary["catalog_total_count"] == 291
    assert summary["importer_format"] == "csv"


def test_generate_taiwan_coa_importer_preview_returns_all_catalog_rows():
    preview = generate_taiwan_coa_importer_preview()
    catalog_count = len(load_taiwan_coa_catalog())
    catalog_rows = [row for row in preview["accounts"] if row["source"] == "official_catalog"]

    assert len(catalog_rows) == catalog_count
    assert preview["summary"]["catalog_total_count"] == catalog_count


def test_generate_and_validate_taiwan_coa_importer_export():
    result = generate_taiwan_coa_importer_files()
    validation = validate_taiwan_coa_importer_export()

    assert result["is_valid"]
    assert validation["is_valid"]
    assert validation["errors"] == []


def test_export_account_numbers_are_unique():
    preview = generate_taiwan_coa_importer_preview()
    account_numbers = [row["account_number"] for row in preview["accounts"]]

    assert len(account_numbers) == len(set(account_numbers))


def test_duplicate_official_names_remain_separate_export_codes():
    preview = generate_taiwan_coa_importer_preview()
    rows_by_code = {row["code"]: row for row in preview["accounts"]}

    assert "0100005" in rows_by_code
    assert "0300090" in rows_by_code
    assert rows_by_code["0100005"]["official_item_name"] == "營業成本"
    assert rows_by_code["0300090"]["official_item_name"] == "營業成本"


def test_core_codes_are_present_in_export():
    preview = generate_taiwan_coa_importer_preview()
    exported_codes = {row["code"] for row in preview["accounts"]}

    assert CORE_ENABLED_CODES - exported_codes == set()


def test_disabled_rows_are_in_post_import_disable_plan_when_importer_does_not_support_disabled():
    result = generate_taiwan_coa_importer_files()

    if not DISABLED_SUPPORTED_BY_IMPORTER:
        validation = result["validation"]
        assert validation["is_valid"]
        assert "exports/chart_of_accounts/taiwan_used_car_full_coa_113_post_import_disable_plan.json" in result[
            "files"
        ]


def test_export_service_does_not_require_database_connection():
    preview = generate_taiwan_coa_importer_preview()

    assert preview["accounts"]
    assert preview["disabled_supported_by_importer"] is False
