from types import SimpleNamespace

from used_car_erp.used_car_erp.services import formal_submitted_sales_invoice_test_fixture_setup_service as service


class UnsafeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def insert(self):
		if self.doctype != "Used Car Vehicle":
			raise AssertionError(f"Unexpected insert: {self.doctype}")
		self.name = "UCV-FIXTURE-001"
		self.stock_no = "VH-FIXTURE-001"
		if hasattr(self, "_fake_db"):
			self._fake_db.vehicles[self.name] = self
		return self

	def save(self):
		return None

	def submit(self):
		raise AssertionError("submit must not be called")

	def delete(self):
		raise AssertionError("delete must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set cleanup must not be called")


class FakeMeta:
	def __init__(self, fields=None):
		self.fields = set(fields or [])

	def has_field(self, fieldname):
		return fieldname in self.fields


class FakeDB:
	def __init__(self):
		self.counts = {doctype: 0 for doctype in service.COUNT_DOCTYPES}
		self.sales_invoices = {}
		self.vehicles = {}
		self.companies = {"OO": UnsafeDoc(name="OO", stock_adjustment_account="0100005-UC - 中古車銷貨成本 - O")}
		self.accounts = {
			"0100005-UC - 中古車銷貨成本 - O": UnsafeDoc(
				name="0100005-UC - 中古車銷貨成本 - O",
				company="OO",
				is_group=0,
				disabled=0,
				root_type="Expense",
			)
		}
		self.warehouses = {}
		self.get_value_map = {}
		self.delete_called = False
		self.cancel_called = False
		self.db_set_called = False

	def count(self, doctype, filters=None):
		if doctype == "Sales Invoice" and filters == {"docstatus": 1}:
			return self.counts.get("Sales Invoice docstatus=1", 0)
		return self.counts.get(doctype, 0)

	def exists(self, doctype, filters):
		if doctype == "Sales Invoice":
			if isinstance(filters, str):
				return filters in self.sales_invoices
			return bool(self.get_value(doctype, filters, "name"))
		if doctype == "Used Car Vehicle":
			if isinstance(filters, str):
				return filters in self.vehicles
			return bool(self.get_value(doctype, filters, "name"))
		if doctype == "Company":
			return filters in self.companies
		if doctype == "Account":
			return filters in self.accounts
		if doctype == "Warehouse":
			return filters in self.warehouses
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		key = (doctype, _freeze(filters), fieldname)
		if key in self.get_value_map:
			return self.get_value_map[key]
		if doctype == "Used Car Vehicle" and isinstance(filters, str):
			return getattr(self.vehicles[filters], fieldname, None)
		if doctype == "Company" and isinstance(filters, str):
			return getattr(self.companies[filters], fieldname, None)
		if doctype == "Warehouse" and isinstance(filters, str):
			return getattr(self.warehouses[filters], fieldname, None)
		return None

	def get_all(self, *args, **kwargs):
		return []

	def set_value(self, *args, **kwargs):
		self.db_set_called = True
		raise AssertionError("db.set_value must not be called")

	def commit(self):
		return None

	def rollback(self):
		raise AssertionError("rollback cleanup must not be called")


class FakeFrappe:
	def __init__(self, db, site="erpnext-coa.test"):
		self.db = db
		self.local = SimpleNamespace(site=site)

	def get_meta(self, doctype):
		if doctype in {"Company", "Stock Entry Detail", "Stock Entry", "Used Car Vehicle"}:
			return FakeMeta({"stock_adjustment_account", "expense_account", "stock_entry_type", "notes", "tax_review_note", "purchase_note"})
		return FakeMeta()

	def get_doc(self, doctype, name=None):
		if isinstance(doctype, dict):
			doc = UnsafeDoc(**doctype)
			doc._fake_db = self.db
			return doc
		if doctype == "Sales Invoice":
			return self.db.sales_invoices[name]
		if doctype == "Used Car Vehicle":
			return self.db.vehicles[name]
		if doctype == "Account":
			return self.db.accounts[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

	def generate_hash(self, length=8):
		return "ABCDEF12"[:length]

	def delete_doc(self, *args, **kwargs):
		self.db.delete_called = True
		raise AssertionError("delete_doc must not be called")

	def whitelist(self):
		return lambda fn: fn


class FakeIntakeService:
	called = 0
	exception = None

	def complete_intake(self, vehicle_name):
		type(self).called += 1
		CALLS.append("intake")
		if self.exception:
			raise self.exception
		return {"item": "ITEM-FIXTURE", "serial_no": "VIN-FIXTURE", "stock_entry": "STE-FIXTURE", "stock_no": "VH-FIXTURE-001"}


class FakeListingService:
	called = 0

	def list_vehicle(self, vehicle_name):
		type(self).called += 1
		CALLS.append("listing")
		return {"status": "上架中"}


class FakeReservationService:
	def create_reservation(self, **kwargs):
		CALLS.append("reservation")
		return {
			"reservation": "RES-FIXTURE",
			"customer": "CUST-FIXTURE",
			"money_flow": "MF-DEPOSIT",
			"voucher_draft": "VD-DEPOSIT",
		}

	def create_final_payment_for_active_reservation(self, **kwargs):
		CALLS.append("final_payment")
		return {"reservation": "RES-FIXTURE", "money_flow": "MF-FINAL", "voucher_draft": "VD-FINAL"}

	def preflight_delivery_for_active_reservation(self, vehicle_name):
		CALLS.append("delivery_preflight")
		return {
			"reservation": "RES-FIXTURE",
			"deposit_money_flow": "MF-DEPOSIT",
			"deposit_voucher_draft": "VD-DEPOSIT",
			"deposit_journal_entry": "JE-DEPOSIT",
			"final_money_flow": "MF-FINAL",
			"final_voucher_draft": "VD-FINAL",
			"final_journal_entry": "JE-FINAL",
		}

	def complete_active_reservation(self, vehicle_name, completion_note=None):
		CALLS.append("complete_reservation")
		return {"vehicle_status": "已售出", "reservation_status": "已完成"}


class FakeVoucherService:
	def confirm_voucher_draft(self, voucher_draft_name, review_note=None):
		if voucher_draft_name == "VD-DEPOSIT":
			CALLS.append("confirm_deposit")
			return {"journal_entry": "JE-DEPOSIT"}
		CALLS.append("confirm_final")
		return {"journal_entry": "JE-FINAL"}


class FakeReadinessService:
	report = None
	called = 0

	def run(self, vehicle_name=None):
		type(self).called += 1
		CALLS.append("readiness")
		return dict(self.report)


class FakeDraftCreationService:
	report = None
	called = 0

	def run(self, vehicle_name=None, note=None):
		type(self).called += 1
		CALLS.append("draft_creation")
		return dict(self.report)


class FakeSnapshotService:
	report = None
	called = 0

	def run(self, sales_invoice=None):
		type(self).called += 1
		CALLS.append("snapshot")
		return dict(self.report, sales_invoice=sales_invoice)


CALLS = []


def _fake_environment(monkeypatch, site="erpnext-coa.test"):
	db = FakeDB()
	frappe = FakeFrappe(db, site=site)
	monkeypatch.setattr(service, "frappe", frappe)
	monkeypatch.setattr(service, "VehicleIntakeService", FakeIntakeService)
	monkeypatch.setattr(service, "VehicleListingService", FakeListingService)
	monkeypatch.setattr(service, "VehicleReservationService", FakeReservationService)
	monkeypatch.setattr(service, "VehicleVoucherService", FakeVoucherService)
	monkeypatch.setattr(service, "FormalSalesInvoiceDraftReadinessService", FakeReadinessService)
	monkeypatch.setattr(service, "GuardedFormalSalesInvoiceDraftCreationQAService", FakeDraftCreationService)
	monkeypatch.setattr(service, "SubmittedSalesInvoiceSubmitGateSnapshotService", FakeSnapshotService)
	monkeypatch.setattr(service.VehicleStockService, "_resolve_company_for_stock_entry", lambda self, vehicle: "OO")
	CALLS.clear()
	FakeIntakeService.called = 0
	FakeIntakeService.exception = None
	FakeListingService.called = 0
	FakeReadinessService.called = 0
	FakeDraftCreationService.called = 0
	FakeSnapshotService.called = 0
	FakeReadinessService.report = _readiness_report()
	FakeDraftCreationService.report = _draft_report()
	FakeSnapshotService.report = _snapshot_report()
	db.sales_invoices["SINV-FIXTURE"] = UnsafeDoc(name="SINV-FIXTURE", docstatus=0, remarks="formal draft")
	return db


def _freeze(value):
	if isinstance(value, dict):
		return tuple(sorted((key, _freeze(val)) for key, val in value.items()))
	if isinstance(value, list):
		return tuple(value)
	return value


def _readiness_report(**overrides):
	data = {"status": "pass", "ready_to_create_sales_invoice_draft": True, "vehicle": "UCV-FIXTURE-001"}
	data.update(overrides)
	return data


def _draft_report(**overrides):
	data = {"status": "pass", "created": True, "sales_invoice": "SINV-FIXTURE", "sales_invoice_docstatus": 0}
	data.update(overrides)
	return data


def _snapshot_report(**overrides):
	data = {"status": "pass", "ready_for_submit_test": True, "blocking_errors": []}
	data.update(overrides)
	return data


def test_non_expected_site_blocks_without_create(monkeypatch):
	_fake_environment(monkeypatch, site="erpnext.localhost")

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "blocked"
	assert FakeIntakeService.called == 0


def test_submitted_sales_invoice_count_blocks_without_create(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice docstatus=1"] = 1

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "blocked"
	assert FakeIntakeService.called == 0


def test_existing_fixture_draft_runs_snapshot_without_recreate(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-EXISTING"] = UnsafeDoc(
		name="UCV-EXISTING",
		stock_no="VH-EXISTING",
		item="ITEM-EXISTING",
		serial_no="VIN-EXISTING",
		stock_entry="STE-EXISTING",
		completed_reservation="RES-EXISTING",
		sales_invoice="SINV-FIXTURE",
	)
	db.get_value_map[("Used Car Vehicle", _freeze({"license_plate": ["like", "%P1-ACC-6F-C%"]}), "name")] = "UCV-EXISTING"

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "pass"
	assert report["created_fixture"] is False
	assert FakeIntakeService.called == 0
	assert FakeSnapshotService.called == 1


def test_clean_site_calls_formal_flow_in_order(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "pass"
	assert CALLS == [
		"intake",
		"listing",
		"reservation",
		"confirm_deposit",
		"final_payment",
		"confirm_final",
		"delivery_preflight",
		"complete_reservation",
		"readiness",
		"draft_creation",
		"snapshot",
	]


def test_readiness_fail_does_not_call_guarded_creation(monkeypatch):
	_fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(status="fail", ready_to_create_sales_invoice_draft=False)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "fail"
	assert FakeDraftCreationService.called == 0


def test_guarded_creation_blocked_reports_fail_without_submit(monkeypatch):
	_fake_environment(monkeypatch)
	FakeDraftCreationService.report = _draft_report(status="blocked", created=False, sales_invoice=None)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "fail"
	assert report["sales_invoice"] is None


def test_created_draft_snapshot_fail_reports_warning_and_keeps_invoice(monkeypatch):
	_fake_environment(monkeypatch)
	FakeSnapshotService.report = _snapshot_report(status="fail", ready_for_submit_test=False, blocking_errors=["not ready"])

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "warning"
	assert report["sales_invoice"] == "SINV-FIXTURE"


def test_snapshot_pass_sets_ready_for_submit_test(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "pass"
	assert report["ready_for_submit_test"] is True


def test_service_does_not_call_submit_delete_cancel_or_destructive_cleanup(monkeypatch):
	db = _fake_environment(monkeypatch)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "pass"
	assert db.delete_called is False
	assert db.cancel_called is False
	assert db.db_set_called is False


def test_created_documents_records_fixture_documents(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()
	docs = {(row["doctype"], row["name"]) for row in report["created_documents"]}

	assert ("Used Car Vehicle", "UCV-FIXTURE-001") in docs
	assert ("Stock Entry", "STE-FIXTURE") in docs
	assert ("Journal Entry", "JE-DEPOSIT") in docs
	assert ("Journal Entry", "JE-FINAL") in docs
	assert ("Sales Invoice", "SINV-FIXTURE") in docs


def test_intake_stock_gate_failure_reports_difference_account_context(monkeypatch):
	_fake_environment(monkeypatch)
	FakeIntakeService.exception = Exception("missing Difference Account")

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "fail"
	assert report["stock_adjustment_account"] == "0100005-UC - 中古車銷貨成本 - O"
	assert report["stock_entry_difference_account"] == "0100005-UC - 中古車銷貨成本 - O"
	assert any("missing Difference Account" in error for error in report["blocking_errors"])
	assert {row["doctype"] for row in report["created_documents"]} == {"Used Car Vehicle"}


def test_rerun_existing_fixture_does_not_create_second_fixture(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-EXISTING"] = UnsafeDoc(
		name="UCV-EXISTING",
		stock_no="VH-EXISTING",
		item="ITEM-EXISTING",
		serial_no="VIN-EXISTING",
		stock_entry="STE-EXISTING",
		completed_reservation="RES-EXISTING",
		sales_invoice="SINV-FIXTURE",
	)
	db.get_value_map[("Sales Invoice", _freeze({"docstatus": 0, "remarks": ["like", f"%{service.FIXTURE_MARKER}%"]}), "name")] = "SINV-FIXTURE"
	db.get_value_map[("Used Car Vehicle", _freeze({"sales_invoice": "SINV-FIXTURE"}), "name")] = "UCV-EXISTING"

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "pass"
	assert FakeIntakeService.called == 0
	assert FakeDraftCreationService.called == 0
	assert FakeSnapshotService.called == 1
