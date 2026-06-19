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
		self.reservations = {}
		self.money_flows = {}
		self.voucher_drafts = {}
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
		if doctype == "Used Car Reservation":
			if isinstance(filters, str):
				return filters in self.reservations
			return bool(self.get_value(doctype, filters, "name"))
		if doctype == "Used Car Money Flow":
			if isinstance(filters, str):
				return filters in self.money_flows
			return bool(self.get_value(doctype, filters, "name"))
		if doctype == "Used Car Voucher Draft":
			if isinstance(filters, str):
				return filters in self.voucher_drafts
			return bool(self.get_value(doctype, filters, "name"))
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
		if doctype in {"Used Car Reservation", "Used Car Money Flow", "Used Car Voucher Draft"} and isinstance(filters, str):
			store = {
				"Used Car Reservation": self.reservations,
				"Used Car Money Flow": self.money_flows,
				"Used Car Voucher Draft": self.voucher_drafts,
			}[doctype]
			return getattr(store[filters], fieldname, None)
		if doctype == "Used Car Reservation" and isinstance(filters, dict):
			return self._match_first(self.reservations, filters, fieldname)
		if doctype == "Used Car Money Flow" and isinstance(filters, dict):
			return self._match_first(self.money_flows, filters, fieldname)
		if doctype == "Used Car Voucher Draft" and isinstance(filters, dict):
			return self._match_first(self.voucher_drafts, filters, fieldname)
		return None

	def _match_first(self, store, filters, fieldname):
		for doc in store.values():
			if all(_matches_filter(getattr(doc, key, None), expected) for key, expected in filters.items()):
				return getattr(doc, fieldname, None)
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
		if doctype == "Used Car Reservation":
			return self.db.reservations[name]
		if doctype == "Used Car Money Flow":
			return self.db.money_flows[name]
		if doctype == "Used Car Voucher Draft":
			return self.db.voucher_drafts[name]
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
		DB.reservations["RES-FIXTURE"] = UnsafeDoc(
			name="RES-FIXTURE",
			vehicle=kwargs["vehicle_name"],
			status="有效",
			customer="CUST-FIXTURE",
			money_flow="MF-DEPOSIT",
			voucher_draft="VD-DEPOSIT",
		)
		DB.money_flows["MF-DEPOSIT"] = UnsafeDoc(name="MF-DEPOSIT", reservation="RES-FIXTURE", flow_type="訂金收款", status="待審核")
		DB.voucher_drafts["VD-DEPOSIT"] = UnsafeDoc(name="VD-DEPOSIT", reservation="RES-FIXTURE", money_flow="MF-DEPOSIT", status="待審核", journal_entry=None)
		return {
			"reservation": "RES-FIXTURE",
			"customer": "CUST-FIXTURE",
			"money_flow": "MF-DEPOSIT",
			"voucher_draft": "VD-DEPOSIT",
		}

	def create_final_payment_for_active_reservation(self, **kwargs):
		CALLS.append("final_payment")
		DB.reservations["RES-FIXTURE"].final_money_flow = "MF-FINAL"
		DB.reservations["RES-FIXTURE"].final_voucher_draft = "VD-FINAL"
		DB.money_flows["MF-FINAL"] = UnsafeDoc(name="MF-FINAL", reservation="RES-FIXTURE", flow_type="尾款收款", status="待審核")
		DB.voucher_drafts["VD-FINAL"] = UnsafeDoc(name="VD-FINAL", reservation="RES-FIXTURE", money_flow="MF-FINAL", status="待審核", journal_entry=None)
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
		DB.vehicles[vehicle_name].status = "已售出"
		DB.vehicles[vehicle_name].completed_reservation = "RES-FIXTURE"
		DB.vehicles[vehicle_name].deposit_money_flow = "MF-DEPOSIT"
		DB.vehicles[vehicle_name].deposit_voucher_draft = "VD-DEPOSIT"
		DB.vehicles[vehicle_name].deposit_journal_entry = "JE-DEPOSIT"
		DB.vehicles[vehicle_name].final_money_flow = "MF-FINAL"
		DB.vehicles[vehicle_name].final_voucher_draft = "VD-FINAL"
		DB.vehicles[vehicle_name].final_journal_entry = "JE-FINAL"
		DB.reservations["RES-FIXTURE"].status = "已完成"
		return {"vehicle_status": "已售出", "reservation_status": "已完成"}


class FakeVoucherService:
	def confirm_voucher_draft(self, voucher_draft_name, review_note=None):
		if voucher_draft_name == "VD-DEPOSIT":
			CALLS.append("confirm_deposit")
			DB.voucher_drafts[voucher_draft_name].status = "已入帳"
			DB.voucher_drafts[voucher_draft_name].journal_entry = "JE-DEPOSIT"
			DB.money_flows["MF-DEPOSIT"].status = "已入帳"
			DB.money_flows["MF-DEPOSIT"].journal_entry = "JE-DEPOSIT"
			return {"journal_entry": "JE-DEPOSIT"}
		CALLS.append("confirm_final")
		DB.voucher_drafts[voucher_draft_name].status = "已入帳"
		DB.voucher_drafts[voucher_draft_name].journal_entry = "JE-FINAL"
		DB.money_flows["MF-FINAL"].status = "已入帳"
		DB.money_flows["MF-FINAL"].journal_entry = "JE-FINAL"
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
DB = None


def _fake_environment(monkeypatch, site="erpnext-coa.test"):
	db = FakeDB()
	global DB
	DB = db
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


def _matches_filter(value, expected):
	if isinstance(expected, list):
		operator = expected[0]
		operand = expected[1] if len(expected) > 1 else None
		if operator == "!=":
			return value != operand
		if operator == "in":
			return value in operand
		if operator == "like":
			return str(operand).replace("%", "") in str(value or "")
	return value == expected


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


def _half_fixture(db, *, stocked=True, reservation=False, active=True, deposit="missing", final="missing", sold=False):
	vehicle = UnsafeDoc(
		name="UCV-HALF",
		stock_no="VH-HALF",
		item="ITEM-HALF" if stocked else None,
		serial_no="VIN-HALF" if stocked else None,
		stock_entry="STE-HALF" if stocked else None,
		status="已售出" if sold else "上架中",
		completed_reservation="RES-FIXTURE" if sold or (reservation and not active) else None,
		sales_invoice=None,
		formal_delivery_status=None,
		deposit_money_flow="MF-DEPOSIT" if sold and deposit == "posted" else None,
		deposit_voucher_draft="VD-DEPOSIT" if sold and deposit == "posted" else None,
		deposit_journal_entry="JE-DEPOSIT" if sold and deposit == "posted" else None,
		final_money_flow="MF-FINAL" if sold and final == "posted" else None,
		final_voucher_draft="VD-FINAL" if sold and final == "posted" else None,
		final_journal_entry="JE-FINAL" if sold and final == "posted" else None,
	)
	db.vehicles[vehicle.name] = vehicle
	db.get_value_map[("Used Car Vehicle", _freeze({"license_plate": ["like", "%P1-ACC-6F-C%"]}), "name")] = vehicle.name
	if reservation:
		status = "有效" if active else "已完成"
		db.reservations["RES-FIXTURE"] = UnsafeDoc(name="RES-FIXTURE", vehicle=vehicle.name, status=status, customer="CUST-FIXTURE")
		if deposit != "missing":
			db.reservations["RES-FIXTURE"].money_flow = "MF-DEPOSIT"
			db.reservations["RES-FIXTURE"].voucher_draft = "VD-DEPOSIT"
			posted = deposit == "posted"
			db.money_flows["MF-DEPOSIT"] = UnsafeDoc(name="MF-DEPOSIT", reservation="RES-FIXTURE", flow_type="訂金收款", status="已入帳" if posted else "待審核", journal_entry="JE-DEPOSIT" if posted else None)
			db.voucher_drafts["VD-DEPOSIT"] = UnsafeDoc(name="VD-DEPOSIT", reservation="RES-FIXTURE", money_flow="MF-DEPOSIT", status="已入帳" if posted else "待審核", journal_entry="JE-DEPOSIT" if posted else None)
		if final != "missing":
			db.reservations["RES-FIXTURE"].final_money_flow = "MF-FINAL"
			db.reservations["RES-FIXTURE"].final_voucher_draft = "VD-FINAL"
			posted = final == "posted"
			db.money_flows["MF-FINAL"] = UnsafeDoc(name="MF-FINAL", reservation="RES-FIXTURE", flow_type="尾款收款", status="已入帳" if posted else "待審核", journal_entry="JE-FINAL" if posted else None)
			db.voucher_drafts["VD-FINAL"] = UnsafeDoc(name="VD-FINAL", reservation="RES-FIXTURE", money_flow="MF-FINAL", status="已入帳" if posted else "待審核", journal_entry="JE-FINAL" if posted else None)
	return vehicle


def test_half_fixture_enters_resume_instead_of_immediate_fail(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["resume_mode"] == "half_fixture_resume"
	assert report["status"] == "pass"
	assert "draft_creation" in CALLS


def test_half_fixture_missing_stock_calls_intake(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, stocked=False, reservation=True, deposit="posted", final="posted")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert FakeIntakeService.called == 1


def test_half_fixture_stocked_skips_intake(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert FakeIntakeService.called == 0


def test_half_fixture_missing_reservation_creates_one(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "pass"
	assert CALLS.count("reservation") == 1


def test_half_fixture_active_reservation_does_not_create_second(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert "reservation" not in CALLS


def test_resume_confirms_pending_deposit_voucher(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="pending", final="posted")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert "confirm_deposit" in CALLS


def test_resume_posted_deposit_skips_confirm(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert "confirm_deposit" not in CALLS


def test_resume_missing_final_payment_creates_it(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="missing")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert "final_payment" in CALLS


def test_resume_confirms_pending_final_voucher(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="pending")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert "confirm_final" in CALLS


def test_resume_unsold_vehicle_completes_reservation(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert "delivery_preflight" in CALLS
	assert "complete_reservation" in CALLS


def test_resume_sold_vehicle_skips_complete(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, active=False, deposit="posted", final="posted", sold=True)

	service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert "complete_reservation" not in CALLS


def test_resume_readiness_fail_does_not_create_draft(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")
	FakeReadinessService.report = _readiness_report(status="fail", ready_to_create_sales_invoice_draft=False)

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "fail"
	assert FakeDraftCreationService.called == 0


def test_resume_guarded_creation_runs_snapshot(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert FakeDraftCreationService.called == 1
	assert FakeSnapshotService.called == 1
	assert report["sales_invoice"] == "SINV-FIXTURE"


def test_resume_snapshot_fail_keeps_invoice_and_warns(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")
	FakeSnapshotService.report = _snapshot_report(status="fail", ready_for_submit_test=False, blocking_errors=["not ready"])

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "warning"
	assert report["sales_invoice"] == "SINV-FIXTURE"


def test_resume_blocks_when_submitted_sales_invoice_count_exists(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Sales Invoice docstatus=1"] = 1
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "blocked"
	assert FakeDraftCreationService.called == 0


def test_resume_does_not_call_destructive_operations(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="posted")

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["status"] == "pass"
	assert db.delete_called is False
	assert db.cancel_called is False
	assert db.db_set_called is False


def test_resume_rerun_existing_draft_does_not_create_second_fixture(monkeypatch):
	db = _fake_environment(monkeypatch)
	vehicle = _half_fixture(db, reservation=True, active=False, deposit="posted", final="posted", sold=True)
	vehicle.sales_invoice = "SINV-FIXTURE"
	db.get_value_map[("Sales Invoice", _freeze({"docstatus": 0, "remarks": ["like", f"%{service.FIXTURE_MARKER}%"]}), "name")] = "SINV-FIXTURE"
	db.get_value_map[("Used Car Vehicle", _freeze({"sales_invoice": "SINV-FIXTURE"}), "name")] = vehicle.name

	report = service.FormalSubmittedSalesInvoiceTestFixtureSetupService().run()

	assert report["resume_mode"] == "existing_draft"
	assert FakeDraftCreationService.called == 0
	assert FakeSnapshotService.called == 1


def test_inspect_formal_submit_fixture_resume_state_is_read_only(monkeypatch):
	db = _fake_environment(monkeypatch)
	_half_fixture(db, reservation=True, deposit="posted", final="missing")

	state = service.inspect_formal_submit_fixture_resume_state()

	assert state["resume_mode"] == "half_fixture_resume"
	assert state["resume_state"]["vehicle"] == "UCV-HALF"
	assert db.delete_called is False
	assert db.cancel_called is False
	assert db.db_set_called is False
