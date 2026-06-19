from types import SimpleNamespace

from used_car_erp.used_car_erp.services import guarded_formal_sales_invoice_submit_qa_service as service


class FakeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def submit(self):
		self.submit_calls = getattr(self, "submit_calls", 0) + 1
		if getattr(self, "submit_exception", None):
			raise Exception(self.submit_exception)
		self.docstatus = 1

	def delete(self):
		raise AssertionError("delete must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def insert(self):
		raise AssertionError("insert must not be called")


class FakeDB:
	def __init__(self):
		self.sales_invoices = {"SINV-FORMAL-001": _invoice()}
		self.vehicles = {"UCV-FORMAL-001": _vehicle()}
		self.serials = {"VIN-FORMAL-001": FakeDoc(name="VIN-FORMAL-001", status="Delivered", warehouse=None)}
		self.gl_entries = _gl_entries()
		self.sle_entries = _sle_entries()
		self.counts = {
			"Sales Invoice": 1,
			"Sales Invoice docstatus=1": 0,
			"GL Entry": 2,
			"Stock Ledger Entry": 1,
			"Payment Entry": 0,
			"Journal Entry": 2,
			"Delivery Note": 0,
			"Stock Entry": 1,
		}
		self.commit_calls = 0
		self.forbidden_calls = []

	def count(self, doctype, filters=None):
		if doctype == "Sales Invoice" and filters == {"docstatus": 1}:
			return self.counts["Sales Invoice docstatus=1"]
		return self.counts.get(doctype, 0)

	def exists(self, doctype, filters):
		if doctype == "Sales Invoice":
			return filters in self.sales_invoices
		if doctype == "Serial No":
			return filters in self.serials
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		if doctype == "Used Car Vehicle":
			for vehicle in self.vehicles.values():
				if vehicle.sales_invoice == filters.get("sales_invoice"):
					return vehicle.name
		return None

	def get_all(self, doctype, filters=None, fields=None, order_by=None):
		if doctype == "GL Entry":
			return list(self.gl_entries)
		if doctype == "Stock Ledger Entry":
			return list(self.sle_entries)
		return []

	def commit(self):
		self.commit_calls += 1
		self.counts["Sales Invoice docstatus=1"] = sum(1 for invoice in self.sales_invoices.values() if invoice.docstatus == 1)
		self.counts["GL Entry"] = 2 + len(self.gl_entries)
		self.counts["Stock Ledger Entry"] = 1 + len(self.sle_entries)

	def rollback(self):
		self.forbidden_calls.append("rollback")
		raise AssertionError("rollback must not be called")

	def sql(self, *args, **kwargs):
		self.forbidden_calls.append("sql")
		raise AssertionError("raw SQL must not be called")

	def set_value(self, *args, **kwargs):
		self.forbidden_calls.append("set_value")
		raise AssertionError("set_value must not be called")


class FakeFrappe:
	def __init__(self, db, site="erpnext-coa.test"):
		self.db = db
		self.local = SimpleNamespace(site=site)

	def get_doc(self, doctype, name=None):
		if doctype == "Sales Invoice":
			return self.db.sales_invoices[name]
		if doctype == "Used Car Vehicle":
			return self.db.vehicles[name]
		if doctype == "Serial No":
			return self.db.serials[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

	def delete_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("delete_doc")
		raise AssertionError("delete_doc must not be called")


class FakeSnapshotService:
	report = None

	def _find_latest_formal_draft_sales_invoice(self):
		return "SINV-FORMAL-001"

	def run(self, sales_invoice=None):
		return dict(self.report or _snapshot_report())


def _fake_environment(monkeypatch, site="erpnext-coa.test"):
	db = FakeDB()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db, site=site))
	monkeypatch.setattr(service, "SubmittedSalesInvoiceSubmitGateSnapshotService", FakeSnapshotService)
	FakeSnapshotService.report = _snapshot_report()
	return db


def _invoice(**overrides):
	data = {
		"name": "SINV-FORMAL-001",
		"docstatus": 0,
		"company": service.COMPANY,
		"customer": "CUST-FORMAL-001",
		"update_stock": 1,
		"taxes_and_charges": service.TAX_TEMPLATE,
		"items": [
			FakeDoc(
				item_code="USED-CAR-VEHICLE",
				serial_no="VIN-FORMAL-001",
				warehouse="中古車庫存倉 - O",
				income_account=service.INCOME_ACCOUNT,
				expense_account=service.EXPENSE_ACCOUNT,
			)
		],
		"submit_calls": 0,
	}
	data.update(overrides)
	return FakeDoc(**data)


def _vehicle(**overrides):
	data = {
		"name": "UCV-FORMAL-001",
		"sales_invoice": "SINV-FORMAL-001",
		"status": "已售出",
		"formal_delivery_status": "銷售發票草稿",
	}
	data.update(overrides)
	return FakeDoc(**data)


def _snapshot_report(**overrides):
	data = {"status": "pass", "ready_for_submit_test": True, "sales_invoice": "SINV-FORMAL-001"}
	data.update(overrides)
	return data


def _gl_entries(accounts=None, debit=100, credit=100):
	accounts = accounts or [
		service.RECEIVABLE_ACCOUNT,
		service.INCOME_ACCOUNT,
		service.TAX_ACCOUNT,
		service.INVENTORY_ACCOUNT,
		service.EXPENSE_ACCOUNT,
	]
	return [FakeDoc(account=account, debit=debit if idx == 0 else 0, credit=credit if idx == 1 else 0) for idx, account in enumerate(accounts)]


def _sle_entries():
	return [FakeDoc(item_code="USED-CAR-VEHICLE", warehouse="中古車庫存倉 - O", actual_qty=-1, stock_value_difference=-300000)]


def test_site_not_expected_blocks_without_submit(monkeypatch):
	db = _fake_environment(monkeypatch, site="erpnext.localhost")
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.sales_invoices["SINV-FORMAL-001"].submit_calls == 0


def test_bad_confirmation_token_blocks_without_submit(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", "BAD")
	assert report["status"] == "blocked"
	assert db.sales_invoices["SINV-FORMAL-001"].submit_calls == 0


def test_target_not_found_blocks(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("MISSING", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert any("不存在" in error for error in report["blocking_errors"])


def test_non_draft_target_blocks_when_not_already_submitted_fixture(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-FORMAL-001"].docstatus = 2
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.sales_invoices["SINV-FORMAL-001"].submit_calls == 0


def test_missing_linked_vehicle_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles = {}
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert any("linked Used Car Vehicle" in error for error in report["blocking_errors"])


def test_vehicle_status_not_sold_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].status = "保留中"
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert any("status" in error for error in report["blocking_errors"])


def test_formal_delivery_status_not_draft_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].formal_delivery_status = "已完成"
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert any("formal_delivery_status" in error for error in report["blocking_errors"])


def test_submit_gate_fail_blocks_without_submit(monkeypatch):
	db = _fake_environment(monkeypatch)
	FakeSnapshotService.report = _snapshot_report(status="fail", ready_for_submit_test=False)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.sales_invoices["SINV-FORMAL-001"].submit_calls == 0


def test_existing_submitted_count_blocks_when_target_is_draft(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice docstatus=1"] = 1
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.sales_invoices["SINV-FORMAL-001"].submit_calls == 0


def test_happy_path_submits_once_and_sets_docstatus(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] in {"pass", "warning"}
	assert report["submitted"] is True
	assert db.sales_invoices["SINV-FORMAL-001"].submit_calls == 1
	assert report["sales_invoice_docstatus_after"] == 1


def test_happy_path_count_deltas(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["count_deltas"]["Sales Invoice"] == 0
	assert report["count_deltas"]["Sales Invoice docstatus=1"] == 1
	assert report["count_deltas"]["Payment Entry"] == 0
	assert report["count_deltas"]["Journal Entry"] == 0
	assert report["count_deltas"]["Delivery Note"] == 0
	assert report["count_deltas"]["Stock Entry"] == 0


def test_happy_path_records_gl_and_sle(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["new_gl_entry_count"] > 0
	assert report["new_stock_ledger_entry_count"] > 0


def test_missing_required_gl_account_returns_warning_status(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.gl_entries = _gl_entries(accounts=[service.RECEIVABLE_ACCOUNT, service.INCOME_ACCOUNT, service.TAX_ACCOUNT, service.INVENTORY_ACCOUNT])
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "warning"
	assert any(service.EXPENSE_ACCOUNT in error for error in report["blocking_errors"])


def test_unbalanced_gl_returns_warning_status(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.gl_entries = _gl_entries(debit=100, credit=90)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "warning"
	assert any("debit / credit" in error for error in report["blocking_errors"])


def test_submit_exception_returns_fail(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-FORMAL-001"].submit_exception = "boom"
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "fail"
	assert any("boom" in error for error in report["blocking_errors"])


def test_rerun_on_already_submitted_same_target_does_not_submit(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-FORMAL-001"].docstatus = 1
	db.counts["Sales Invoice docstatus=1"] = 1
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["status"] == "already_submitted"
	assert report["already_submitted"] is True
	assert db.sales_invoices["SINV-FORMAL-001"].submit_calls == 0


def test_service_does_not_call_delete_cancel_raw_sql_or_ignore_mandatory(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert report["submitted"] is True
	assert db.forbidden_calls == []
	assert not hasattr(db.sales_invoices["SINV-FORMAL-001"], "ignore_mandatory")


def test_service_does_not_modify_vehicle_formal_delivery_status(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedFormalSalesInvoiceSubmitQAService().run("SINV-FORMAL-001", service.CONFIRMATION_TOKEN)
	assert db.vehicles["UCV-FORMAL-001"].formal_delivery_status == "銷售發票草稿"
	assert any("formal_delivery_status" in warning for warning in report["warnings"])
