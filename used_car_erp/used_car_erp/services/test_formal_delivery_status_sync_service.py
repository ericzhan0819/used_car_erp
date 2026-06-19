from types import SimpleNamespace

from used_car_erp.used_car_erp.services import formal_delivery_status_sync_service as service
from used_car_erp.used_car_erp.services.used_car_controlled_write_service import assert_controlled_write_policy


class FakeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def submit(self):
		raise AssertionError("submit must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")

	def amend(self):
		raise AssertionError("amend must not be called")

	def delete(self):
		raise AssertionError("delete must not be called")

	def save(self):
		raise AssertionError("save must not be called directly")


class FakeDB:
	def __init__(self):
		self.sales_invoices = {"SINV-FORMAL-001": _invoice()}
		self.vehicles = {"UCV-FORMAL-001": _vehicle()}
		self.counts = {
			"GL Entry": 5,
			"Stock Ledger Entry": 1,
			"Payment Entry": 0,
			"Delivery Note": 0,
			"Purchase Invoice": 0,
			"Journal Entry": 0,
			"Stock Entry": 0,
		}
		self.set_value_calls = []
		self.commit_calls = 0
		self.forbidden_calls = []

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

	def get_all(self, doctype, filters=None, fields=None, order_by=None, limit=None):
		if doctype == "Used Car Vehicle":
			return [
				{"name": vehicle.name, "sales_invoice": vehicle.sales_invoice}
				for vehicle in self.vehicles.values()
				if vehicle.sales_invoice and vehicle.status == "已售出" and vehicle.formal_delivery_status in {"銷售發票草稿", "已完成"}
			]
		return []

	def count(self, doctype, filters=None):
		return self.counts.get(doctype, 0)

	def set_value(self, doctype, name, values, update_modified=True):
		self.set_value_calls.append((doctype, name, dict(values), update_modified))
		vehicle = self.vehicles[name]
		for fieldname, value in values.items():
			setattr(vehicle, fieldname, value)

	def commit(self):
		self.commit_calls += 1

	def rollback(self):
		self.forbidden_calls.append("rollback")
		raise AssertionError("rollback must not be called")

	def sql(self, *args, **kwargs):
		self.forbidden_calls.append("sql")
		raise AssertionError("raw SQL must not be called")


class FakeMeta:
	def has_field(self, fieldname):
		return fieldname in {
			"formal_delivery_status",
			"formal_delivery_completed_at",
			"formal_delivery_completed_by",
			"formal_delivery_note",
			"formal_delivery_posting_date",
		}


class FakeFrappe:
	PermissionError = Exception

	def __init__(self, db, site="erpnext-coa.test"):
		self.db = db
		self.local = SimpleNamespace(site=site)
		self.session = SimpleNamespace(user="accounting@example.com")

	def get_doc(self, doctype, name=None):
		if doctype == "Sales Invoice":
			return self.db.sales_invoices[name]
		if doctype == "Used Car Vehicle":
			return self.db.vehicles[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

	def get_meta(self, doctype):
		assert doctype == "Used Car Vehicle"
		return FakeMeta()

	def get_roles(self, user=None):
		return ["Used Car Accounting"]

	def throw(self, message, exc=None):
		raise exc(message) if exc else Exception(message)

	def delete_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("delete_doc")
		raise AssertionError("delete_doc must not be called")


def _fake_environment(monkeypatch, site="erpnext-coa.test"):
	db = FakeDB()
	fake_frappe = FakeFrappe(db, site=site)
	monkeypatch.setattr(service, "frappe", fake_frappe)
	monkeypatch.setattr("used_car_erp.used_car_erp.services.used_car_controlled_write_service.frappe", fake_frappe)
	monkeypatch.setattr("used_car_erp.used_car_erp.services.used_car_action_permission_service.frappe", fake_frappe)
	monkeypatch.setattr(service, "now", lambda: "2026-06-19 20:00:00")
	return db


def _invoice(**overrides):
	data = {
		"name": "SINV-FORMAL-001",
		"docstatus": 1,
		"posting_date": "2026-06-19",
		"company": service.COMPANY,
		"customer": "CUST-FORMAL-001",
	}
	data.update(overrides)
	return FakeDoc(**data)


def _vehicle(**overrides):
	data = {
		"name": "UCV-FORMAL-001",
		"sales_invoice": "SINV-FORMAL-001",
		"status": "已售出",
		"formal_delivery_status": "銷售發票草稿",
		"formal_delivery_posting_date": None,
		"formal_delivery_completed_at": None,
		"formal_delivery_completed_by": None,
		"formal_delivery_note": None,
	}
	data.update(overrides)
	return FakeDoc(**data)


def test_non_expected_site_blocks_write_without_set_value(monkeypatch):
	db = _fake_environment(monkeypatch, site="erpnext.localhost")
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert report["status"] == "blocked"
	assert db.set_value_calls == []


def test_target_not_found_blocks(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalDeliveryStatusSyncService().inspect("MISSING")
	assert report["status"] == "blocked"
	assert any("不存在" in error for error in report["blocking_errors"])


def test_target_docstatus_not_submitted_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.sales_invoices["SINV-FORMAL-001"].docstatus = 0
	report = service.FormalDeliveryStatusSyncService().inspect("SINV-FORMAL-001")
	assert report["status"] == "blocked"


def test_missing_linked_vehicle_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles = {}
	report = service.FormalDeliveryStatusSyncService().inspect("SINV-FORMAL-001")
	assert report["status"] == "blocked"
	assert any("linked Used Car Vehicle" in error for error in report["blocking_errors"])


def test_vehicle_status_not_sold_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].status = "保留中"
	report = service.FormalDeliveryStatusSyncService().inspect("SINV-FORMAL-001")
	assert report["status"] == "blocked"


def test_vehicle_sales_invoice_mismatch_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].sales_invoice = "OTHER"
	report = service.FormalDeliveryStatusSyncService().inspect("SINV-FORMAL-001")
	assert report["status"] == "blocked"


def test_dry_run_pass_plans_updates(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=1)
	assert report["status"] == "pass"
	assert report["planned_updates"]["formal_delivery_status"] == "已完成"
	assert report["planned_updates"]["formal_delivery_posting_date"] == "2026-06-19"
	assert report["formal_delivery_status_before"] == "銷售發票草稿"
	assert report["formal_delivery_status_after"] == "已完成"


def test_dry_run_does_not_write(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=1)
	assert report["status"] == "pass"
	assert db.set_value_calls == []
	assert db.vehicles["UCV-FORMAL-001"].formal_delivery_status == "銷售發票草稿"


def test_write_mode_updates_only_allowed_fields(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert report["status"] == "pass"
	assert len(db.set_value_calls) == 1
	values = db.set_value_calls[0][2]
	assert set(values) == {
		"formal_delivery_status",
		"formal_delivery_completed_at",
		"formal_delivery_completed_by",
		"formal_delivery_note",
		"formal_delivery_posting_date",
	}


def test_write_mode_sets_completed(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert report["synced"] is True
	assert db.vehicles["UCV-FORMAL-001"].formal_delivery_status == "已完成"
	assert db.vehicles["UCV-FORMAL-001"].formal_delivery_note.endswith("SINV-FORMAL-001")


def test_already_synced_does_not_write(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].formal_delivery_status = "已完成"
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert report["status"] == "already_synced"
	assert report["already_synced"] is True
	assert db.set_value_calls == []


def test_unknown_formal_delivery_status_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-FORMAL-001"].formal_delivery_status = "預收款沖轉草稿"
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert report["status"] == "blocked"
	assert db.set_value_calls == []


def test_missing_gl_entry_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["GL Entry"] = 0
	report = service.FormalDeliveryStatusSyncService().inspect("SINV-FORMAL-001")
	assert report["status"] == "blocked"


def test_missing_stock_ledger_entry_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Stock Ledger Entry"] = 0
	report = service.FormalDeliveryStatusSyncService().inspect("SINV-FORMAL-001")
	assert report["status"] == "blocked"


def test_side_effect_documents_are_warning_not_blocking(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.counts["Payment Entry"] = 1
	db.counts["Delivery Note"] = 1
	db.counts["Purchase Invoice"] = 1
	report = service.FormalDeliveryStatusSyncService().inspect("SINV-FORMAL-001")
	assert report["status"] == "warning"
	assert report["blocking_errors"] == []
	assert len(report["warnings"]) == 3


def test_does_not_create_advance_settlement_journal_entry(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert "advance_settlement_journal_entry" not in report["applied_updates"]
	assert not hasattr(db.vehicles["UCV-FORMAL-001"], "advance_settlement_journal_entry")


def test_does_not_modify_sales_invoice(monkeypatch):
	db = _fake_environment(monkeypatch)
	before = dict(db.sales_invoices["SINV-FORMAL-001"].__dict__)
	service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert dict(db.sales_invoices["SINV-FORMAL-001"].__dict__) == before


def test_does_not_call_submit_cancel_amend_delete(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert report["status"] == "pass"
	assert db.forbidden_calls == []


def test_does_not_use_raw_sql_or_ignore_mandatory(monkeypatch):
	db = _fake_environment(monkeypatch)
	service.FormalDeliveryStatusSyncService().run("SINV-FORMAL-001", dry_run=0)
	assert db.forbidden_calls == []
	assert not hasattr(db.vehicles["UCV-FORMAL-001"], "ignore_mandatory")


def test_controlled_write_unknown_field_not_allowed():
	try:
		assert_controlled_write_policy(service.ACTION, "Used Car Vehicle", {"formal_delivery_status", "sales_invoice"})
	except Exception as exc:
		assert "未授權欄位" in str(exc)
	else:
		raise AssertionError("unknown field must not be allowed")
