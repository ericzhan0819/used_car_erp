import csv
from pathlib import Path

from used_car_erp.used_car_erp.services import taiwan_coa_import_preflight_service as service


class FakeDB:
    def __init__(self):
        self.doctypes = set(service.COUNT_DOCTYPES) | {"DocType"}
        self.company_abbr = "O"
        self.columns = {
            "Account": {
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
                "creation",
                "modified",
                "lft",
            },
            "Sales Invoice": {"name", "company", "docstatus"},
            "Purchase Invoice": {"name", "company", "docstatus"},
            "Payment Entry": {"name", "company", "docstatus"},
            "Journal Entry": {"name", "company", "docstatus"},
            "Stock Entry": {"name", "company", "docstatus"},
            "Delivery Note": {"name", "company", "docstatus"},
            "Purchase Receipt": {"name", "company", "docstatus"},
            "GL Entry": {"name", "company"},
            "Stock Ledger Entry": {"name", "company"},
            "Company": {"name", "abbr"},
        }
        self.counts = {}
        self.accounts = [
            {
                "name": "Cash - O",
                "account_number": "1111",
                "account_name": "Cash",
                "parent_account": "Assets - O",
                "root_type": "Asset",
                "report_type": "Balance Sheet",
                "account_type": "Cash",
                "is_group": 0,
                "disabled": 0,
                "company": "OO",
                "account_currency": "TWD",
                "creation": "2026-01-01 00:00:00",
                "modified": "2026-01-01 00:00:00",
            }
        ]
        self.forbidden_calls = []

    def exists(self, doctype, name):
        if doctype == "DocType":
            return name in self.doctypes
        if doctype == "Company" and name == "OO":
            return True
        return False

    def get_value(self, doctype, name, fieldname):
        if doctype == "Company" and name == "OO" and fieldname == "abbr":
            return self.company_abbr
        return None

    def get_table_columns(self, table):
        return list(self.columns.get(table, {"name"}))

    def count(self, doctype, filters=None):
        key = (doctype, tuple(sorted((filters or {}).items())))
        return self.counts.get(key, self.counts.get((doctype, ()), 0))

    def get_all(self, doctype, filters=None, fields=None, order_by=None):
        if doctype == "Account":
            return [{field: row.get(field) for field in fields} for row in self.accounts]
        return []

    def save(self, *args, **kwargs):
        self.forbidden_calls.append("save")

    def insert(self, *args, **kwargs):
        self.forbidden_calls.append("insert")

    def delete(self, *args, **kwargs):
        self.forbidden_calls.append("delete")

    def db_set(self, *args, **kwargs):
        self.forbidden_calls.append("db_set")

    def commit(self, *args, **kwargs):
        self.forbidden_calls.append("commit")

    def rollback(self, *args, **kwargs):
        self.forbidden_calls.append("rollback")


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "_repo_root", lambda: tmp_path)
    return tmp_path / "exports" / "chart_of_accounts"


def _write_importer_artefacts(export_dir):
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "taiwan_used_car_full_coa_113_preview.json").write_text("{}\n", encoding="utf-8")
    (export_dir / "taiwan_used_car_full_coa_113.csv").write_text("Account Name\n", encoding="utf-8")
    (export_dir / "taiwan_used_car_full_coa_113_post_import_disable_plan.json").write_text(
        "{}\n", encoding="utf-8"
    )


def _patch_fake_db(monkeypatch, fake_db):
    monkeypatch.setattr(service.frappe, "db", fake_db)


def _patch_validation(monkeypatch, is_valid=True):
    monkeypatch.setattr(
        service,
        "validate_taiwan_coa_importer_export",
        lambda: {"is_valid": is_valid, "errors": [] if is_valid else ["invalid"], "warnings": []},
    )


def test_get_chart_of_accounts_import_preflight_summary_can_run(monkeypatch, tmp_path):
    export_dir = _patch_paths(monkeypatch, tmp_path)
    _write_importer_artefacts(export_dir)
    fake_db = FakeDB()
    _patch_fake_db(monkeypatch, fake_db)

    summary = service.get_chart_of_accounts_import_preflight_summary()

    assert summary["company"] == "OO"
    assert summary["company_exists"] is True
    assert summary["company_abbr"] == "O"
    assert summary["required_manual_confirmation"] is True


def test_export_current_account_backup_writes_csv_with_fake_db(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    fake_db = FakeDB()
    _patch_fake_db(monkeypatch, fake_db)

    result = service.export_current_account_backup()

    backup_path = tmp_path / result["path"]
    with backup_path.open(encoding="utf-8") as backup_file:
        rows = list(csv.DictReader(backup_file))

    assert result["exists"] is True
    assert rows[0]["name"] == "Cash - O"
    assert "old_parent" in result["missing_fields"]


def test_generate_accounting_data_counts_handles_existing_and_missing_doctypes(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    fake_db = FakeDB()
    fake_db.doctypes.remove("Used Car Voucher Draft")
    fake_db.counts[("GL Entry", (("company", "OO"),))] = 2
    fake_db.counts[("Sales Invoice", (("company", "OO"), ("docstatus", 1)))] = 1
    _patch_fake_db(monkeypatch, fake_db)

    payload = service.generate_accounting_data_counts()
    rows = {row["doctype"]: row for row in payload["counts"]}

    assert rows["GL Entry"]["exists"] is True
    assert rows["GL Entry"]["count"] == 2
    assert rows["Sales Invoice"]["submitted_count"] == 1
    assert rows["Used Car Voucher Draft"]["exists"] is False
    assert rows["Used Car Voucher Draft"]["warning"] == "DocType not found"


def test_gate_report_can_generate_warning_when_gl_entry_exists(monkeypatch, tmp_path):
    export_dir = _patch_paths(monkeypatch, tmp_path)
    _write_importer_artefacts(export_dir)
    fake_db = FakeDB()
    fake_db.counts[("GL Entry", (("company", "OO"),))] = 1
    _patch_fake_db(monkeypatch, fake_db)
    _patch_validation(monkeypatch)

    service.export_current_account_backup()
    service.generate_accounting_data_counts()
    report = service.generate_chart_of_accounts_import_gate_report()

    assert report["status"] == "warning"
    assert report["can_import_chart_of_accounts"] is False
    assert report["required_manual_confirmation"] is True
    assert "GL Entry count is greater than 0." in report["warnings"]


def test_gate_report_can_generate_warning_without_formal_data(monkeypatch, tmp_path):
    export_dir = _patch_paths(monkeypatch, tmp_path)
    _write_importer_artefacts(export_dir)
    fake_db = FakeDB()
    _patch_fake_db(monkeypatch, fake_db)
    _patch_validation(monkeypatch)

    service.export_current_account_backup()
    service.generate_accounting_data_counts()
    report = service.generate_chart_of_accounts_import_gate_report()

    assert report["status"] == "warning"
    assert report["can_import_chart_of_accounts"] is True
    assert report["required_manual_confirmation"] is True


def test_gate_report_fails_when_importer_artefact_missing(monkeypatch, tmp_path):
    export_dir = _patch_paths(monkeypatch, tmp_path)
    export_dir.mkdir(parents=True, exist_ok=True)
    fake_db = FakeDB()
    _patch_fake_db(monkeypatch, fake_db)
    _patch_validation(monkeypatch, is_valid=False)

    service.export_current_account_backup()
    service.generate_accounting_data_counts()
    report = service.generate_chart_of_accounts_import_gate_report()

    assert report["status"] == "fail"
    assert report["can_import_chart_of_accounts"] is False
    assert any(gate["status"] == "fail" for gate in report["gates"])


def test_preflight_does_not_call_forbidden_write_methods(monkeypatch, tmp_path):
    export_dir = _patch_paths(monkeypatch, tmp_path)
    _write_importer_artefacts(export_dir)
    fake_db = FakeDB()
    _patch_fake_db(monkeypatch, fake_db)
    _patch_validation(monkeypatch)

    service.run_chart_of_accounts_import_preflight()

    assert fake_db.forbidden_calls == []
