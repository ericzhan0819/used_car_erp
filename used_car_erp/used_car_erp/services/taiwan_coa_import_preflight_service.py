import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import frappe

from used_car_erp.used_car_erp.services.taiwan_coa_importer_export_service import (
    validate_taiwan_coa_importer_export,
)


COMPANY = "OO"
COMPANY_ABBR = "O"
ACCOUNT_BACKUP_FIELDS = [
    "name",
    "account_number",
    "account_name",
    "parent_account",
    "root_type",
    "report_type",
    "account_type",
    "is_group",
    "disabled",
    "company",
    "account_currency",
    "old_parent",
    "creation",
    "modified",
]
COUNT_DOCTYPES = [
    "Company",
    "Account",
    "GL Entry",
    "Sales Invoice",
    "Purchase Invoice",
    "Payment Entry",
    "Journal Entry",
    "Stock Ledger Entry",
    "Stock Entry",
    "Delivery Note",
    "Purchase Receipt",
    "Item",
    "Warehouse",
    "Sales Taxes and Charges Template",
    "Purchase Taxes and Charges Template",
    "Used Car Vehicle",
    "Used Car Reservation",
    "Used Car Money Flow",
    "Used Car Voucher Draft",
    "Used Car Vehicle Cost",
    "Taiwan Accounting Item Code",
    "Taiwan Accounting Item Account Mapping",
]
FORMAL_WARNING_RULES = [
    ("GL Entry", "count", "GL Entry count is greater than 0."),
    ("Sales Invoice", "submitted_count", "Submitted Sales Invoice count is greater than 0."),
    ("Purchase Invoice", "submitted_count", "Submitted Purchase Invoice count is greater than 0."),
    ("Payment Entry", "submitted_count", "Submitted Payment Entry count is greater than 0."),
    ("Journal Entry", "submitted_count", "Submitted Journal Entry count is greater than 0."),
    ("Stock Ledger Entry", "count", "Stock Ledger Entry count is greater than 0."),
    ("Stock Entry", "submitted_count", "Submitted Stock Entry count is greater than 0."),
    ("Delivery Note", "submitted_count", "Submitted Delivery Note count is greater than 0."),
    ("Purchase Receipt", "submitted_count", "Submitted Purchase Receipt count is greater than 0."),
]


def _repo_root():
    return Path(__file__).resolve().parents[3]


def _export_dir():
    return _repo_root() / "exports" / "chart_of_accounts"


def _preflight_dir():
    return _export_dir() / "preflight"


def _backup_path():
    return _preflight_dir() / "current_account_backup.csv"


def _counts_path():
    return _preflight_dir() / "accounting_data_counts.json"


def _gate_report_path():
    return _preflight_dir() / "pre_import_gate_report.json"


def _preview_path():
    return _export_dir() / "taiwan_used_car_full_coa_113_preview.json"


def _importer_csv_path():
    return _export_dir() / "taiwan_used_car_full_coa_113.csv"


def _disable_plan_path():
    return _export_dir() / "taiwan_used_car_full_coa_113_post_import_disable_plan.json"


def _relative(path):
    return str(path.relative_to(_repo_root()))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _doctype_exists(doctype):
    return bool(frappe.db.exists("DocType", doctype))


def _table_columns(doctype):
    try:
        return set(frappe.db.get_table_columns(doctype))
    except Exception:
        return set()


def _has_company_field(doctype):
    return "company" in _table_columns(doctype)


def _has_docstatus_field(doctype):
    return "docstatus" in _table_columns(doctype)


def _safe_count(doctype, filters=None):
    return frappe.db.count(doctype, filters=filters or {})


def _company_filters(doctype, company):
    if _has_company_field(doctype):
        return {"company": company}
    return {}


def _read_json(path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def _load_counts_by_doctype():
    payload = _read_json(_counts_path()) or {}
    return {row.get("doctype"): row for row in payload.get("counts", [])}


def _load_gate_report():
    return _read_json(_gate_report_path()) or {}


def _artefact_paths():
    return {
        "current_account_backup_csv": _relative(_backup_path()),
        "accounting_data_counts_json": _relative(_counts_path()),
        "pre_import_gate_report_json": _relative(_gate_report_path()),
        "preview_json": _relative(_preview_path()),
        "importer_csv": _relative(_importer_csv_path()),
        "disable_plan": _relative(_disable_plan_path()),
    }


def _check_required_importer_artefacts():
    return [
        {"name": "preview_json_exists", "path": _relative(_preview_path()), "exists": _preview_path().exists()},
        {"name": "importer_csv_exists", "path": _relative(_importer_csv_path()), "exists": _importer_csv_path().exists()},
        {"name": "disable_plan_exists", "path": _relative(_disable_plan_path()), "exists": _disable_plan_path().exists()},
    ]


def export_current_account_backup(company=COMPANY):
    _preflight_dir().mkdir(parents=True, exist_ok=True)
    columns = _table_columns("Account")
    available_fields = [field for field in ACCOUNT_BACKUP_FIELDS if field in columns]
    missing_fields = [field for field in ACCOUNT_BACKUP_FIELDS if field not in columns]
    filters = {"company": company} if "company" in columns else {}
    rows = frappe.db.get_all(
        "Account",
        filters=filters,
        fields=available_fields,
        order_by="lft asc" if "lft" in columns else "name asc",
    )

    with _backup_path().open("w", newline="", encoding="utf-8") as backup_file:
        writer = csv.DictWriter(backup_file, fieldnames=available_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in available_fields})

    return {
        "company": company,
        "path": _relative(_backup_path()),
        "exists": _backup_path().exists(),
        "row_count": len(rows),
        "fields": available_fields,
        "missing_fields": missing_fields,
        "warnings": [
            "Account backup skipped missing columns: " + ", ".join(missing_fields)
        ]
        if missing_fields
        else [],
    }


def _count_doctype(doctype, company):
    if not _doctype_exists(doctype):
        return {
            "doctype": doctype,
            "exists": False,
            "count": None,
            "draft_count": None,
            "submitted_count": None,
            "cancelled_count": None,
            "warning": "DocType not found",
        }

    filters = _company_filters(doctype, company)
    result = {
        "doctype": doctype,
        "exists": True,
        "count": _safe_count(doctype, filters),
        "draft_count": None,
        "submitted_count": None,
        "cancelled_count": None,
        "warning": None,
    }

    if _has_docstatus_field(doctype):
        result["draft_count"] = _safe_count(doctype, {**filters, "docstatus": 0})
        result["submitted_count"] = _safe_count(doctype, {**filters, "docstatus": 1})
        result["cancelled_count"] = _safe_count(doctype, {**filters, "docstatus": 2})

    if not filters and doctype not in {"Company", "Item", "Taiwan Accounting Item Code"}:
        result["warning"] = "No company field; count is site-wide."
    return result


def generate_accounting_data_counts(company=COMPANY):
    _preflight_dir().mkdir(parents=True, exist_ok=True)
    counts = [_count_doctype(doctype, company) for doctype in COUNT_DOCTYPES]
    payload = {"company": company, "generated_at": _now(), "counts": counts}
    _counts_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _company_info(company):
    exists = bool(frappe.db.exists("Company", company))
    abbr = frappe.db.get_value("Company", company, "abbr") if exists else None
    return exists, abbr


def _gate(name, ok, pass_details, fail_details, errors):
    status = "pass" if ok else "fail"
    if not ok:
        errors.append(fail_details)
    return {"name": name, "status": status, "details": pass_details if ok else fail_details}


def _formal_data_warnings(counts_by_doctype):
    warnings = []
    for doctype, field, message in FORMAL_WARNING_RULES:
        row = counts_by_doctype.get(doctype) or {}
        if (row.get(field) or 0) > 0:
            warnings.append(message)
    return warnings


def _draft_or_custom_warnings(counts_by_doctype):
    warnings = []
    for doctype, row in counts_by_doctype.items():
        if not row or not row.get("exists"):
            continue
        if (row.get("draft_count") or 0) > 0:
            warnings.append(f"{doctype} draft count is greater than 0; manual confirmation is required.")
    for doctype in [
        "Used Car Vehicle",
        "Used Car Reservation",
        "Used Car Money Flow",
        "Used Car Voucher Draft",
        "Used Car Vehicle Cost",
        "Taiwan Accounting Item Account Mapping",
    ]:
        row = counts_by_doctype.get(doctype) or {}
        if (row.get("count") or 0) > 0:
            warnings.append(f"{doctype} count is greater than 0; dev site overwrite requires manual review.")
    return warnings


def generate_chart_of_accounts_import_gate_report(company=COMPANY):
    _preflight_dir().mkdir(parents=True, exist_ok=True)
    warnings = []
    errors = []
    gates = []

    company_exists, company_abbr = _company_info(company)
    gates.append(
        _gate(
            "company_exists",
            company_exists,
            f"Company {company} exists.",
            f"Company {company} does not exist.",
            errors,
        )
    )
    gates.append(
        _gate(
            "company_abbr",
            company_abbr == COMPANY_ABBR,
            f"Company abbreviation is {COMPANY_ABBR}.",
            f"Company abbreviation is {company_abbr}; expected {COMPANY_ABBR}.",
            errors,
        )
    )

    for artefact in _check_required_importer_artefacts():
        gates.append(
            _gate(
                artefact["name"],
                artefact["exists"],
                f"{artefact['path']} exists.",
                f"{artefact['path']} is missing.",
                errors,
            )
        )

    try:
        importer_validation = validate_taiwan_coa_importer_export()
    except Exception as exc:
        importer_validation = {"is_valid": False, "errors": [str(exc)], "warnings": []}
    warnings.extend(importer_validation.get("warnings", []))
    errors.extend(importer_validation.get("errors", []))
    gates.append(
        {
            "name": "importer_validation",
            "status": "pass" if importer_validation.get("is_valid") else "fail",
            "details": "P1-ACC-5 importer validation passed."
            if importer_validation.get("is_valid")
            else "P1-ACC-5 importer validation failed.",
        }
    )

    if not _backup_path().exists():
        try:
            backup = export_current_account_backup(company)
            warnings.extend(backup.get("warnings", []))
        except Exception as exc:
            backup = {"exists": False, "warnings": [], "error": str(exc)}
            errors.append(f"current_account_backup.csv could not be generated: {exc}")
    gates.append(
        _gate(
            "current_account_backup_generated",
            _backup_path().exists(),
            "current_account_backup.csv has been generated.",
            "current_account_backup.csv has not been generated.",
            errors,
        )
    )

    if not _counts_path().exists():
        try:
            generate_accounting_data_counts(company)
        except Exception as exc:
            errors.append(f"accounting_data_counts.json could not be generated: {exc}")
    gates.append(
        _gate(
            "accounting_data_counts_generated",
            _counts_path().exists(),
            "accounting_data_counts.json has been generated.",
            "accounting_data_counts.json has not been generated.",
            errors,
        )
    )

    counts_by_doctype = _load_counts_by_doctype()
    for row in counts_by_doctype.values():
        if row.get("warning"):
            warnings.append(f"{row['doctype']}: {row['warning']}")
    warnings.extend(_formal_data_warnings(counts_by_doctype))
    warnings.extend(_draft_or_custom_warnings(counts_by_doctype))
    warnings = sorted(set(warnings))
    errors = sorted(set(errors))
    has_failed_gate = any(gate["status"] == "fail" for gate in gates)
    status = "fail" if has_failed_gate or errors else "warning"
    can_import = not has_failed_gate and not errors and not _formal_data_warnings(counts_by_doctype)

    payload = {
        "company": company,
        "company_exists": company_exists,
        "company_abbr": company_abbr,
        "generated_at": _now(),
        "status": status,
        "can_import_chart_of_accounts": can_import,
        "required_manual_confirmation": True,
        "gates": gates,
        "warnings": warnings,
        "errors": errors,
        "artefacts": _artefact_paths(),
    }
    _gate_report_path().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def run_chart_of_accounts_import_preflight(company=COMPANY):
    backup = export_current_account_backup(company)
    counts = generate_accounting_data_counts(company)
    gate_report = generate_chart_of_accounts_import_gate_report(company)
    return {"backup": backup, "counts": counts, "gate_report": gate_report}


def validate_chart_of_accounts_import_preflight_files(company=COMPANY):
    report = _load_gate_report()
    files = {
        "current_account_backup_csv": _backup_path().exists(),
        "accounting_data_counts_json": _counts_path().exists(),
        "pre_import_gate_report_json": _gate_report_path().exists(),
    }
    errors = [f"{name} is missing" for name, exists in files.items() if not exists]
    if report and report.get("company") != company:
        errors.append(f"pre_import_gate_report company is {report.get('company')}; expected {company}")
    return {
        "company": company,
        "is_valid": not errors,
        "files": files,
        "status": report.get("status") if report else "not_generated",
        "can_import_chart_of_accounts": report.get("can_import_chart_of_accounts", False),
        "required_manual_confirmation": True,
        "warnings": report.get("warnings", []) if report else [],
        "errors": errors + (report.get("errors", []) if report else []),
    }


def get_chart_of_accounts_import_preflight_summary(company=COMPANY):
    company_exists, company_abbr = _company_info(company)
    counts_by_doctype = _load_counts_by_doctype()
    gate_report = _load_gate_report()
    account_row = counts_by_doctype.get("Account") or {}
    gl_row = counts_by_doctype.get("GL Entry") or {}
    sales_invoice_row = counts_by_doctype.get("Sales Invoice") or {}
    purchase_invoice_row = counts_by_doctype.get("Purchase Invoice") or {}
    payment_entry_row = counts_by_doctype.get("Payment Entry") or {}
    journal_entry_row = counts_by_doctype.get("Journal Entry") or {}
    stock_ledger_row = counts_by_doctype.get("Stock Ledger Entry") or {}

    return {
        "company": company,
        "company_exists": company_exists,
        "company_abbr": company_abbr,
        "current_account_count": account_row.get("count") or 0,
        "gl_entry_count": gl_row.get("count") or 0,
        "submitted_sales_invoice_count": sales_invoice_row.get("submitted_count") or 0,
        "submitted_purchase_invoice_count": purchase_invoice_row.get("submitted_count") or 0,
        "submitted_payment_entry_count": payment_entry_row.get("submitted_count") or 0,
        "submitted_journal_entry_count": journal_entry_row.get("submitted_count") or 0,
        "stock_ledger_entry_count": stock_ledger_row.get("count") or 0,
        "importer_csv_exists": _importer_csv_path().exists(),
        "disable_plan_exists": _disable_plan_path().exists(),
        "preflight_status": gate_report.get("status", "not_generated"),
        "can_import_chart_of_accounts": gate_report.get("can_import_chart_of_accounts", False),
        "required_manual_confirmation": True,
        "warnings": gate_report.get("warnings", []),
        "errors": gate_report.get("errors", []),
    }
