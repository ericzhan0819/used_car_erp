from types import SimpleNamespace

from used_car_erp.used_car_erp.services import submitted_sales_invoice_submit_gate_snapshot_service as service


class UnsafeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def submit(self):
		raise AssertionError("submit must not be called")

	def insert(self):
		raise AssertionError("insert must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")

	def delete(self):
		raise AssertionError("delete must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")


class FakeDB:
	def __init__(self):
		self.counts = {doctype: 0 for doctype in service.COUNT_DOCTYPES}
		self.sales_invoices = {}
		self.vehicles = {}
		self.forbidden_called = False

	def count(self, doctype, filters=None):
		if doctype == "Sales Invoice" and filters == {"docstatus": 1}:
			return self.counts.get("Sales Invoice docstatus=1", 0)
		return self.counts.get(doctype, 0)

	def exists(self, doctype, filters):
		if doctype == "Sales Invoice":
			return filters in self.sales_invoices
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		if doctype == "Used Car Vehicle":
			for vehicle in self.vehicles.values():
				if vehicle.sales_invoice == filters.get("sales_invoice"):
					return vehicle.name
		return None

	def set_value(self, *args, **kwargs):
		self.forbidden_called = True
		raise AssertionError("set_value must not be called")

	def commit(self):
		self.forbidden_called = True
		raise AssertionError("commit must not be called")

	def rollback(self):
		self.forbidden_called = True
		raise AssertionError("rollback must not be called")


class FakeFrappe:
	def __init__(self, db):
		self.db = db

	def get_doc(self, doctype, name=None):
		if doctype == "Sales Invoice":
			return self.db.sales_invoices[name]
		if doctype == "Used Car Vehicle":
			return self.db.vehicles[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")


class FakePreflightService:
	called_with = []
	report = None

	def run(self, sales_invoice=None):
		type(self).called_with.append(sales_invoice)
		return dict(self.report)


def _fake_environment(monkeypatch):
	db = FakeDB()
	db.sales_invoices["SINV-FORMAL-001"] = _invoice()
	db.sales_invoices["SINV-QA-001"] = _invoice(name="SINV-QA-001", remarks="P1-ACC-6E QA Draft Sales Invoice")
	db.vehicles["UCV-FORMAL-001"] = _vehicle()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	monkeypatch.setattr(service, "SubmittedSalesInvoicePreflightService", FakePreflightService)
	monkeypatch.setattr(
		service,
		"find_formal_vehicle_sales_invoice_preflight_candidates",
		lambda limit=1: [{"sales_invoice": "SINV-FORMAL-001", "vehicle": "UCV-FORMAL-001"}],
	)
	FakePreflightService.called_with = []
	FakePreflightService.report = _preflight_report()
	return db


def _invoice(**overrides):
	data = {
		"name": "SINV-FORMAL-001",
		"company": service.COMPANY,
		"customer": "CUST-FORMAL-001",
		"docstatus": 0,
		"update_stock": 1,
		"posting_date": "2026-06-19",
		"due_date": "2026-06-19",
		"taxes_and_charges": service.TAX_TEMPLATE,
		"remarks": "中古車正式銷售草稿",
		"items": [
			UnsafeDoc(
				item_code="USED-CAR-VEHICLE",
				qty=1,
				rate=1000000,
				serial_no="VIN-FORMAL-001",
				warehouse="中古車庫存倉 - O",
				income_account="0100001-UC - 中古車銷售收入 - O",
				expense_account="0100005-UC - 中古車銷貨成本 - O",
			)
		],
		"taxes": [
			UnsafeDoc(
				charge_type="On Net Total",
				account_head=service.TAX_ACCOUNT,
				rate=5,
				included_in_print_rate=1,
			)
		],
	}
	data.update(overrides)
	return UnsafeDoc(**data)


def _vehicle(**overrides):
	data = {
		"name": "UCV-FORMAL-001",
		"sales_invoice": "SINV-FORMAL-001",
		"status": "已售出",
		"formal_delivery_status": "銷售發票草稿",
		"item": "USED-CAR-VEHICLE",
		"serial_no": "VIN-FORMAL-001",
		"completed_reservation": "RES-FORMAL-001",
	}
	data.update(overrides)
	return UnsafeDoc(**data)


def _preflight_report(**overrides):
	data = {
		"status": "pass",
		"ready_to_submit": True,
		"sales_invoice": "SINV-FORMAL-001",
		"target_mode": "formal_vehicle_draft",
		"baseline_mode": "formal_flow_observe_only",
		"blocking_errors": [],
		"warnings": [],
	}
	data.update(overrides)
	return data


def test_not_found_formal_draft_fails(monkeypatch):
	_fake_environment(monkeypatch)
	monkeypatch.setattr(service, "find_formal_vehicle_sales_invoice_preflight_candidates", lambda limit=1: [])

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert report["ready_for_submit_test"] is False
	assert "找不到正式車輛流程 Draft Sales Invoice。" in report["blocking_errors"]


def test_explicit_sales_invoice_is_checked_directly(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run(sales_invoice="SINV-FORMAL-001")

	assert report["sales_invoice"] == "SINV-FORMAL-001"
	assert FakePreflightService.called_with == ["SINV-FORMAL-001"]


def test_default_target_does_not_pick_qa_draft(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["sales_invoice"] == "SINV-FORMAL-001"
	assert report["sales_invoice"] != "SINV-QA-001"


def test_formal_draft_with_linked_vehicle_and_preflight_passes(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "pass"
	assert report["ready_for_submit_test"] is True
	assert report["vehicle"] == "UCV-FORMAL-001"
	assert report["preflight_status"] == "pass"
	assert report["target_mode"] == "formal_vehicle_draft"
	assert report["baseline_mode"] == "formal_flow_observe_only"


def test_docstatus_non_zero_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-FORMAL-001"].docstatus = 1

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert any("docstatus" in error for error in report["blocking_errors"])


def test_update_stock_not_one_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-FORMAL-001"].update_stock = 0

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert any("update_stock" in error for error in report["blocking_errors"])


def test_missing_linked_vehicle_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles = {}

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert any("linked Used Car Vehicle" in error for error in report["blocking_errors"])


def test_vehicle_status_not_sold_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].status = "保留中"

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert any("status 必須是 已售出" in error for error in report["blocking_errors"])


def test_formal_delivery_status_not_draft_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].formal_delivery_status = "已完成"

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert any("formal_delivery_status" in error for error in report["blocking_errors"])


def test_item_row_missing_required_fields_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	row = db.sales_invoices["SINV-FORMAL-001"].items[0]
	row.serial_no = None
	row.warehouse = None
	row.income_account = None

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert any("serial_no" in error for error in report["blocking_errors"])
	assert any("warehouse" in error for error in report["blocking_errors"])
	assert any("income_account" in error for error in report["blocking_errors"])


def test_tax_row_mismatch_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-FORMAL-001"].taxes_and_charges = "BAD"
	tax = db.sales_invoices["SINV-FORMAL-001"].taxes[0]
	tax.charge_type = "Actual"
	tax.account_head = "BAD"
	tax.rate = 4
	tax.included_in_print_rate = 0

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert any("taxes_and_charges" in error for error in report["blocking_errors"])
	assert any("charge_type" in error for error in report["blocking_errors"])
	assert any("account_head" in error for error in report["blocking_errors"])
	assert any("rate" in error for error in report["blocking_errors"])
	assert any("included_in_print_rate" in error for error in report["blocking_errors"])


def test_preflight_fail_makes_submit_gate_fail(monkeypatch):
	_fake_environment(monkeypatch)
	FakePreflightService.report = _preflight_report(status="fail", ready_to_submit=False, blocking_errors=["preflight blocked"])

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "fail"
	assert report["ready_for_submit_test"] is False
	assert any("PreflightService" in error for error in report["blocking_errors"])


def test_formal_gl_sle_baseline_counts_do_not_fail_snapshot(monkeypatch):
	_fake_environment(monkeypatch)
	FakePreflightService.report = _preflight_report(
		gl_entry_count=2,
		stock_ledger_entry_count=3,
		validations=[
			"formal flow baseline observed: GL Entry count = 2",
			"formal flow baseline observed: Stock Ledger Entry count = 3",
		],
		warnings=[],
	)

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "pass"
	assert report["ready_for_submit_test"] is True
	assert report["preflight_report"]["gl_entry_count"] == 2
	assert report["preflight_report"]["stock_ledger_entry_count"] == 3


def test_submitted_sales_invoice_count_warning(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice docstatus=1"] = 1

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "warning"
	assert report["ready_for_submit_test"] is False
	assert any("submitted Sales Invoice" in warning for warning in report["warnings"])


def test_service_does_not_call_forbidden_write_methods(monkeypatch):
	db = _fake_environment(monkeypatch)

	report = service.SubmittedSalesInvoiceSubmitGateSnapshotService().run()

	assert report["status"] == "pass"
	assert db.forbidden_called is False
	assert list(report.keys()) == list(service.REPORT_KEYS)
