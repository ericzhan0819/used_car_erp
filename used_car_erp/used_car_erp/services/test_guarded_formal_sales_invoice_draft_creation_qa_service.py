from types import SimpleNamespace

from used_car_erp.used_car_erp.services import guarded_formal_sales_invoice_draft_creation_qa_service as service


class UnsafeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def submit(self):
		raise AssertionError("submit must not be called")

	def delete(self):
		raise AssertionError("delete must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")

	def save(self):
		raise AssertionError("save must not be called")


class FakeDB:
	def __init__(self):
		self.counts = {doctype: 0 for doctype in service.COUNT_DOCTYPES}
		self.sales_invoices = {}
		self.set_value_called = False

	def count(self, doctype, filters=None):
		return self.counts.get(doctype, 0)

	def exists(self, doctype, filters):
		if doctype == "Sales Invoice":
			return filters in self.sales_invoices
		return False

	def set_value(self, *args, **kwargs):
		self.set_value_called = True
		raise AssertionError("set_value must not be called")


class FakeFrappe:
	def __init__(self, db):
		self.db = db

	def get_doc(self, doctype, name=None):
		if doctype == "Sales Invoice":
			return self.db.sales_invoices[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

	def whitelist(self):
		return lambda fn: fn


class FakeReadinessService:
	report = None

	def run(self, vehicle_name=None):
		return dict(self.report)


class FakeVehicleReservationService:
	called = 0
	result = None
	exception = None

	def create_sales_invoice_draft_for_vehicle(self, vehicle_name, posting_date=None, note=None):
		type(self).called += 1
		if self.exception:
			raise self.exception
		return dict(self.result)


class FakeSubmittedPreflightService:
	called = 0
	report = None

	def run(self, sales_invoice=None):
		type(self).called += 1
		return dict(self.report)


def _fake_environment(monkeypatch):
	db = FakeDB()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	monkeypatch.setattr(service, "FormalSalesInvoiceDraftReadinessService", FakeReadinessService)
	monkeypatch.setattr(service, "VehicleReservationService", FakeVehicleReservationService)
	monkeypatch.setattr(service, "SubmittedSalesInvoicePreflightService", FakeSubmittedPreflightService)
	monkeypatch.setattr(service, "run_latest_formal_vehicle_sales_invoice_preflight", lambda: _preflight_report())
	FakeReadinessService.report = _readiness_report()
	FakeVehicleReservationService.called = 0
	FakeVehicleReservationService.result = _creation_result()
	FakeVehicleReservationService.exception = None
	FakeSubmittedPreflightService.called = 0
	FakeSubmittedPreflightService.report = _preflight_report()
	db.sales_invoices["SINV-GUARDED-001"] = _invoice()
	return db


def _readiness_report(**overrides):
	data = {
		"status": "pass",
		"ready_to_create_sales_invoice_draft": True,
		"vehicle": "UCV-GUARDED-001",
		"reservation": "RES-GUARDED-001",
	}
	data.update(overrides)
	return data


def _creation_result(**overrides):
	data = {
		"vehicle_name": "UCV-GUARDED-001",
		"reservation": "RES-GUARDED-001",
		"sales_invoice": "SINV-GUARDED-001",
		"formal_delivery_status": "銷售發票草稿",
	}
	data.update(overrides)
	return data


def _preflight_report(**overrides):
	data = {
		"status": "pass",
		"ready_to_submit": True,
		"sales_invoice": "SINV-GUARDED-001",
		"blocking_errors": [],
	}
	data.update(overrides)
	return data


def _invoice(**overrides):
	data = {
		"name": "SINV-GUARDED-001",
		"docstatus": 0,
		"update_stock": 1,
		"taxes_and_charges": service.SALES_TAX_TEMPLATE,
		"items": [
			UnsafeDoc(
				serial_no="VIN-GUARDED-001",
				warehouse="中古車庫存倉 - O",
				income_account="0100001-UC - 中古車銷售收入 - O",
			)
		],
		"taxes": [
			UnsafeDoc(
				charge_type="On Net Total",
				account_head=service.SALES_TAX_ACCOUNT,
				rate=service.SALES_TAX_RATE,
				included_in_print_rate=1,
			)
		],
	}
	data.update(overrides)
	return UnsafeDoc(**data)


def test_readiness_fail_blocks_without_create(monkeypatch):
	_fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(status="fail", ready_to_create_sales_invoice_draft=False)

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert report["status"] == "blocked"
	assert report["created"] is False
	assert FakeVehicleReservationService.called == 0


def test_readiness_warning_blocks_without_create(monkeypatch):
	_fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(status="warning", ready_to_create_sales_invoice_draft=False)

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert report["status"] == "blocked"
	assert FakeVehicleReservationService.called == 0


def test_readiness_pass_calls_create_once(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice"] = 1

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert FakeVehicleReservationService.called == 1
	assert report["created"] is True


def test_created_invoice_docstatus_checked(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-GUARDED-001"].docstatus = 1
	db.counts["Sales Invoice"] = 1

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert report["sales_invoice_docstatus"] == 1
	assert any("docstatus 必須是 0" in error for error in report["blocking_errors"])


def test_tax_template_and_tax_row_checked(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-GUARDED-001"].taxes_and_charges = "BAD"
	db.sales_invoices["SINV-GUARDED-001"].taxes[0].account_head = "BAD-TAX"
	db.counts["Sales Invoice"] = 1

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert any("taxes_and_charges" in error for error in report["blocking_errors"])
	assert any("account_head" in error for error in report["blocking_errors"])


def test_item_row_serial_warehouse_income_checked(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-GUARDED-001"].items[0].serial_no = None
	db.sales_invoices["SINV-GUARDED-001"].items[0].warehouse = None
	db.sales_invoices["SINV-GUARDED-001"].items[0].income_account = None
	db.counts["Sales Invoice"] = 1

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert any("serial_no" in error for error in report["blocking_errors"])
	assert any("warehouse" in error for error in report["blocking_errors"])
	assert any("income_account" in error for error in report["blocking_errors"])


def test_restricted_counts_must_not_change(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts.update({"Sales Invoice": 1, "GL Entry": 1, "Stock Ledger Entry": 1})
	original_count = db.count

	def count_after_change(doctype, filters=None):
		if FakeVehicleReservationService.called and doctype == "GL Entry":
			return 2
		return original_count(doctype, filters=filters)

	db.count = count_after_change

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert any("GL Entry count 不可改變" in error for error in report["blocking_errors"])


def test_sales_invoice_count_must_increase_one(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice"] = 1

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert any("Sales Invoice count 必須增加 1" in error for error in report["blocking_errors"])


def test_create_then_calls_submitted_preflight(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice"] = 1

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert FakeSubmittedPreflightService.called == 1
	assert report["preflight_status"] == "pass"
	assert report["ready_for_submit_preflight"] is True


def test_create_exception_returns_fail_with_message(monkeypatch):
	_fake_environment(monkeypatch)
	FakeVehicleReservationService.exception = RuntimeError("boom")

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert report["status"] == "fail"
	assert report["created"] is False
	assert any("boom" in error for error in report["blocking_errors"])


def test_service_does_not_call_forbidden_write_methods(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice"] = 1

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert report["created"] is True
	assert db.set_value_called is False
	assert list(report.keys()) == list(service.REPORT_KEYS)


def test_preflight_fail_reports_created_without_repair(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice"] = 1
	FakeSubmittedPreflightService.report = _preflight_report(status="fail", ready_to_submit=False, blocking_errors=["serial blocked"])

	report = service.GuardedFormalSalesInvoiceDraftCreationQAService().run()

	assert report["created"] is True
	assert report["preflight_status"] == "fail"
	assert report["status"] == "warning"
	assert any("preflight 未通過" in error for error in report["blocking_errors"])
