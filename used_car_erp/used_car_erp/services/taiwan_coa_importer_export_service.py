import csv
import json
from collections import Counter
from pathlib import Path

from used_car_erp.used_car_erp.services.taiwan_coa_catalog_service import (
    CORE_ENABLED_CODES,
    REQUIRED_REVIEW_CODES,
    SOURCE_YEAR,
    load_taiwan_coa_catalog,
    validate_taiwan_coa_catalog,
)


IMPORTER_FORMAT = "csv"
DISABLED_SUPPORTED_BY_IMPORTER = False
CSV_HEADERS = [
    "Account Name",
    "Parent Account",
    "Account Number",
    "Parent Account Number",
    "Is Group",
    "Account Type",
    "Root Type",
    "Account Currency",
]
ROOT_TYPES = {"Asset", "Liability", "Equity", "Income", "Expense"}
GENERATED_GROUPS = {
    "Asset": {"account_number": "TW-ASSET", "account_name": "資產"},
    "Liability": {"account_number": "TW-LIABILITY", "account_name": "負債"},
    "Equity": {"account_number": "TW-EQUITY", "account_name": "權益"},
    "Income": {"account_number": "TW-INCOME", "account_name": "收入"},
    "Expense": {"account_number": "TW-EXPENSE", "account_name": "費用"},
}


def _repo_root():
    return Path(__file__).resolve().parents[3]


def _export_dir():
    return _repo_root() / "exports" / "chart_of_accounts"


def _preview_path():
    return _export_dir() / "taiwan_used_car_full_coa_113_preview.json"


def _csv_path():
    return _export_dir() / "taiwan_used_car_full_coa_113.csv"


def _disable_plan_path():
    return _export_dir() / "taiwan_used_car_full_coa_113_post_import_disable_plan.json"


def _generated_group_rows():
    rows = []
    for root_type, group in GENERATED_GROUPS.items():
        rows.append(
            {
                "source_year": SOURCE_YEAR,
                "code": group["account_number"],
                "official_item_name": group["account_name"],
                "account_number": group["account_number"],
                "account_name": group["account_name"],
                "root_type": root_type,
                "report_type": "Balance Sheet"
                if root_type in {"Asset", "Liability", "Equity"}
                else "Profit and Loss",
                "parent_code": None,
                "parent_account_name": None,
                "parent_account": None,
                "is_group": 1,
                "account_type": None,
                "is_enabled_by_default": 1,
                "disabled": 0,
                "manual_review_required": 0,
                "source": "generated_hierarchy_group",
                "source_note": "Generated ERPNext importer root group; not an official Taiwan code.",
            }
        )
    return rows


def _resolve_parent(row, catalog_by_code):
    parent_code = row.get("parent_code")
    if parent_code and catalog_by_code.get(parent_code):
        return catalog_by_code[parent_code]["account_name"], catalog_by_code[parent_code]["account_number"]
    if row.get("parent_account_name"):
        return row["parent_account_name"], parent_code or ""
    group = GENERATED_GROUPS[row["root_type"]]
    return group["account_name"], group["account_number"]


def _build_preview_rows():
    catalog = load_taiwan_coa_catalog()
    catalog_by_code = {row["code"]: row for row in catalog}
    preview_rows = _generated_group_rows()

    for row in catalog:
        parent_name, parent_number = _resolve_parent(row, catalog_by_code)
        preview_rows.append(
            {
                "source_year": row["source_year"],
                "code": row["code"],
                "official_item_name": row["official_item_name"],
                "account_number": row["account_number"],
                "account_name": row["account_name"],
                "root_type": row["root_type"],
                "report_type": row["report_type"],
                "parent_code": parent_number,
                "parent_account_name": parent_name,
                "parent_account": parent_name,
                "is_group": row["is_group"],
                "account_type": row.get("account_type"),
                "is_enabled_by_default": row["is_enabled_by_default"],
                "disabled": 0 if row["is_enabled_by_default"] else 1,
                "manual_review_required": row["manual_review_required"],
                "source": "official_catalog",
                "source_note": row.get("source_note") or "",
                "disabled_reason": row.get("disabled_reason"),
            }
        )
    return preview_rows


def _manual_review_codes(rows):
    return sorted(row["code"] for row in rows if row.get("manual_review_required") == 1)


def _summary_from_rows(rows):
    catalog_rows = [row for row in rows if row.get("source") == "official_catalog"]
    generated_rows = [row for row in rows if row.get("source") == "generated_hierarchy_group"]
    manual_review_codes = _manual_review_codes(catalog_rows)
    warnings = []
    review_posting_codes = sorted(set(manual_review_codes) & REQUIRED_REVIEW_CODES)
    if review_posting_codes:
        warnings.append(
            "Manual review required before import for posting-sensitive codes: "
            + ", ".join(review_posting_codes)
        )
    if not DISABLED_SUPPORTED_BY_IMPORTER:
        warnings.append(
            "ERPNext Chart of Accounts Importer does not support disabled; post-import disable plan is required."
        )

    return {
        "source_year": SOURCE_YEAR,
        "catalog_total_count": len(catalog_rows),
        "export_account_count": len(rows),
        "enabled_count": sum(1 for row in catalog_rows if row["is_enabled_by_default"] == 1),
        "disabled_count": sum(1 for row in catalog_rows if row["is_enabled_by_default"] == 0),
        "group_count": sum(1 for row in rows if row["is_group"] == 1),
        "ledger_count": sum(1 for row in rows if row["is_group"] == 0),
        "generated_group_count": len(generated_rows),
        "manual_review_required_count": len(manual_review_codes),
        "manual_review_required_codes": manual_review_codes,
        "importer_format": IMPORTER_FORMAT,
        "disabled_supported_by_importer": DISABLED_SUPPORTED_BY_IMPORTER,
        "post_import_disable_plan_required": not DISABLED_SUPPORTED_BY_IMPORTER,
        "missing_parent_count": sum(
            1 for row in rows if row["is_group"] == 0 and not row.get("parent_account")
        ),
        "manual_review_blocking_count": 0,
        "warnings": warnings,
        "errors": [],
    }


def get_taiwan_coa_importer_export_summary():
    return _summary_from_rows(_build_preview_rows())


def generate_taiwan_coa_importer_preview():
    rows = _build_preview_rows()
    payload = {
        "source_year": SOURCE_YEAR,
        "importer_format": IMPORTER_FORMAT,
        "disabled_supported_by_importer": DISABLED_SUPPORTED_BY_IMPORTER,
        "summary": _summary_from_rows(rows),
        "accounts": rows,
    }
    _export_dir().mkdir(parents=True, exist_ok=True)
    _preview_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _write_csv(rows):
    with _csv_path().open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CSV_HEADERS)
        for row in rows:
            writer.writerow(
                [
                    row["account_name"],
                    row.get("parent_account") or "",
                    row["account_number"],
                    row.get("parent_code") or "",
                    row["is_group"],
                    row.get("account_type") or "",
                    row["root_type"] if not row.get("parent_account") else "",
                    "",
                ]
            )


def _write_disable_plan(rows):
    disabled_rows = [
        row
        for row in rows
        if row.get("source") == "official_catalog" and row.get("disabled") == 1
    ]
    payload = {
        "source_year": SOURCE_YEAR,
        "reason": "ERPNext Chart of Accounts Importer does not support disabled field in this version.",
        "accounts_to_disable": [
            {
                "code": row["code"],
                "account_number": row["account_number"],
                "account_name": row["account_name"],
                "expected_erpnext_account_name": f"{row['account_number']} - {row['account_name']} - O",
                "disabled_reason": row.get("disabled_reason") or "Disabled by source catalog policy.",
            }
            for row in disabled_rows
        ],
    }
    _disable_plan_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def generate_taiwan_coa_importer_files():
    catalog_validation = validate_taiwan_coa_catalog()
    if not catalog_validation["is_valid"]:
        return {
            "is_valid": False,
            "errors": catalog_validation["errors"],
            "warnings": catalog_validation["warnings"],
            "files": [],
        }

    preview = generate_taiwan_coa_importer_preview()
    rows = preview["accounts"]
    _write_csv(rows)
    disable_plan = _write_disable_plan(rows) if not DISABLED_SUPPORTED_BY_IMPORTER else None
    validation = validate_taiwan_coa_importer_export()

    files = [str(_preview_path().relative_to(_repo_root())), str(_csv_path().relative_to(_repo_root()))]
    if disable_plan:
        files.append(str(_disable_plan_path().relative_to(_repo_root())))

    return {
        "is_valid": validation["is_valid"],
        "summary": preview["summary"],
        "validation": validation,
        "files": files,
    }


def _load_preview_file():
    with _preview_path().open(encoding="utf-8") as preview_file:
        return json.load(preview_file)


def _load_disable_plan_file():
    with _disable_plan_path().open(encoding="utf-8") as plan_file:
        return json.load(plan_file)


def validate_taiwan_coa_importer_export():
    errors = []
    warnings = []

    if not _preview_path().exists():
        errors.append("preview JSON export file does not exist")
        return {"is_valid": False, "errors": errors, "warnings": warnings}
    if not _csv_path().exists():
        errors.append("CSV importer file does not exist")

    preview = _load_preview_file()
    rows = preview.get("accounts", [])
    catalog_rows = [row for row in rows if row.get("source") == "official_catalog"]
    generated_rows = [row for row in rows if row.get("source") == "generated_hierarchy_group"]
    catalog_count = len(load_taiwan_coa_catalog())

    if len(catalog_rows) != catalog_count:
        errors.append(f"preview catalog row count mismatch: {len(catalog_rows)} != {catalog_count}")

    account_numbers = [row.get("account_number") for row in rows]
    duplicates = sorted(code for code, count in Counter(account_numbers).items() if code and count > 1)
    if duplicates:
        errors.append("duplicate account_number values: " + ", ".join(duplicates))

    for row in rows:
        code = row.get("code") or "unknown"
        if not row.get("account_number"):
            errors.append(f"{code}: account_number is required")
        if not row.get("account_name"):
            errors.append(f"{code}: account_name is required")
        if row.get("root_type") not in ROOT_TYPES:
            errors.append(f"{code}: root_type is invalid")
        if row.get("is_group") not in {0, 1}:
            errors.append(f"{code}: is_group must be 0 or 1")
        if row.get("is_group") == 0 and not row.get("parent_account"):
            errors.append(f"{code}: ledger account must have parent")

    preview_codes = {row["code"] for row in catalog_rows}
    required_codes = CORE_ENABLED_CODES | REQUIRED_REVIEW_CODES
    missing_required_codes = sorted(required_codes - preview_codes)
    if missing_required_codes:
        errors.append("missing required export codes: " + ", ".join(missing_required_codes))
    if not {"0100005", "0300090"}.issubset(preview_codes):
        errors.append("0100005 and 0300090 must both exist in export")

    if not DISABLED_SUPPORTED_BY_IMPORTER:
        if not _disable_plan_path().exists():
            errors.append("post-import disable plan is required but does not exist")
        else:
            disable_plan = _load_disable_plan_file()
            disabled_codes = {row["code"] for row in catalog_rows if row.get("disabled") == 1}
            plan_codes = {row["code"] for row in disable_plan.get("accounts_to_disable", [])}
            missing_plan_codes = sorted(disabled_codes - plan_codes)
            if missing_plan_codes:
                errors.append("disabled rows missing from disable plan: " + ", ".join(missing_plan_codes))

    if len(generated_rows) != len(GENERATED_GROUPS):
        errors.append("generated hierarchy root group count mismatch")

    if not errors:
        warnings.extend(preview.get("summary", {}).get("warnings", []))

    return {
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": preview.get("summary", {}),
    }
