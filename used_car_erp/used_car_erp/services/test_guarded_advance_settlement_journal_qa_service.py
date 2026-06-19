from types import SimpleNamespace

from used_car_erp.used_car_erp.services import guarded_advance_settlement_journal_qa_service as service
from used_car_erp.used_car_erp.services import used_car_controlled_write_service as controlled_write


class FakeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def insert(self):
		if getattr(self, "insert_exception", None):
			raise Exception(self.insert_exception)
		self.name = getattr(self, "name", None) or "JE-SETTLE-001"
		return self

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


class FakeDB:
	def __init__(self):
		self.vehicles = {"UCV-SETTLE-001": _vehicle()}
		self.sales_invoices = {"SINV-SETTLE-001": _invoice()}
		self.journal_entries = {}
		self.counts = {
			"Journal Entry": 2,
			"GL Entry": 4,
			"Sales Invoice": 1,
			"Sales Invoice docstatus=1": 1,
			"Payment Entry": 0,
			"Delivery Note": 0,
			"Stock Entry": 1,
			"Purchase Invoice": 0,
		}
		self.gl_entries = []
		self.set_value_calls = []
		self.commit_calls = 0
		self.forbidden_calls = []

	def count(self, doctype, filters=None):
		if doctype == "Sales Invoice" and filters == {"docstatus": 1}:
			return self.counts["Sales Invoice docstatus=1"]
		return self.counts.get(doctype, 0)

	def exists(self, doctype, name):
		if doctype == "Used Car Vehicle":
			return name in self.vehicles
		if doctype == "Sales Invoice":
			return name in self.sales_invoices
		if doctype == "Journal Entry":
			return name in self.journal_entries
		return False

	def get_value(self, doctype, filters, fieldname=None, order_by=None):
		if doctype == "Journal Entry" and fieldname == "docstatus":
			return self.journal_entries.get(filters, FakeDoc(docstatus=None)).docstatus
		return None

	def get_all(self, doctype, filters=None, fields=None, order_by=None):
		if doctype == "GL Entry" and filters == {"voucher_type": "Journal Entry", "voucher_no": "JE-SETTLE-001"}:
			return list(self.gl_entries)
		return []

	def set_value(self, doctype, name, values, update_modified=True):
		self.set_value_calls.append((doctype, name, values, update_modified))
		for fieldname, value in values.items():
			setattr(self.vehicles[name], fieldname, value)

	def commit(self):
		self.commit_calls += 1
		if self.journal_entries.get("JE-SETTLE-001", FakeDoc(docstatus=0)).docstatus == 1:
			self.counts["Journal Entry"] = 3
			self.counts["GL Entry"] = 6
			self.sales_invoices["SINV-SETTLE-001"].outstanding_amount = getattr(self, "outstanding_after", 0)
			self.gl_entries = [
				FakeDoc(account="2203 - 預收款 - O", debit=100, credit=0),
				FakeDoc(account=service.report_receivable_for_test if hasattr(service, "report_receivable_for_test") else "1122 - 應收帳款 - O", debit=0, credit=100),
			]

	def rollback(self):
		self.forbidden_calls.append("rollback")
		raise AssertionError("rollback must not be called")

	def sql(self, *args, **kwargs):
		self.forbidden_calls.append("sql")
		raise AssertionError("raw SQL must not be called")


class FakeMeta:
	def __init__(self, fields):
		self.fields = set(fields)

	def has_field(self, fieldname):
		return fieldname in self.fields


class FakeFrappe:
	def __init__(self, db, site="erpnext-coa.test"):
		self.db = db
		self.local = SimpleNamespace(site=site)
		self.session = SimpleNamespace(user="Administrator")

	def get_doc(self, doctype, name=None):
		if isinstance(doctype, dict):
			doc = FakeDoc(**doctype)
			doc.name = "JE-SETTLE-001"
			doc.submit_exception = getattr(self.db, "journal_submit_exception", None)
			original_insert = doc.insert

			def insert():
				inserted = original_insert()
				self.db.journal_entries[inserted.name] = inserted
				return inserted

			doc.insert = insert
			return doc
		if doctype == "Used Car Vehicle":
			return self.db.vehicles[name]
		if doctype == "Sales Invoice":
			return self.db.sales_invoices[name]
		if doctype == "Journal Entry":
			return self.db.journal_entries[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

	def get_meta(self, doctype):
		if doctype == "Journal Entry":
			return FakeMeta({"voucher_type", "remark", "user_remark"})
		return FakeMeta(set())

	def delete_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("delete_doc")
		raise AssertionError("delete_doc must not be called")

	def get_roles(self, user=None):
		return ["System Manager"]

	def throw(self, message, exc=Exception):
		raise exc(message)


class FakeReadinessService:
	report = None

	def run(self, sales_invoice=None, vehicle_name=None):
		return dict(self.report or _readiness_report())


def _fake_environment(monkeypatch, site="erpnext-coa.test"):
	db = FakeDB()
	fake_frappe = FakeFrappe(db, site=site)
	monkeypatch.setattr(service, "frappe", fake_frappe)
	monkeypatch.setattr(controlled_write, "frappe", fake_frappe)
	monkeypatch.setattr(service, "db_set_service_controlled_values", controlled_write.db_set_service_controlled_values)
	monkeypatch.setattr(service, "AdvanceSettlementReadinessService", FakeReadinessService)
	FakeReadinessService.report = _readiness_report()
	return db


def _vehicle(**overrides):
	data = {
		"name": "UCV-SETTLE-001",
		"sales_invoice": "SINV-SETTLE-001",
		"formal_delivery_status": "已完成",
		"advance_settlement_journal_entry": None,
	}
	data.update(overrides)
	return FakeDoc(**data)


def _invoice(**overrides):
	data = {
		"name": "SINV-SETTLE-001",
		"docstatus": 1,
		"company": service.COMPANY,
		"customer": "CUST-001",
		"posting_date": "2026-06-19",
		"outstanding_amount": 100,
	}
	data.update(overrides)
	return FakeDoc(**data)


def _readiness_report(preview=None, **overrides):
	data = {
		"status": "pass",
		"ready_to_create_advance_settlement": True,
		"company": service.COMPANY,
		"sales_invoice": "SINV-SETTLE-001",
		"vehicle": "UCV-SETTLE-001",
		"reservation": "RES-001",
		"customer": "CUST-001",
		"receivable_account": "1122 - 應收帳款 - O",
		"advance_total": 100,
		"settlement_preview": preview if preview is not None else _same_account_preview(),
	}
	data.update(overrides)
	return data


def _same_account_preview():
	return [
		{"account": "2203 - 預收款 - O", "debit": 100, "credit": 0, "reference_type": "Sales Invoice", "reference_name": "SINV-SETTLE-001"},
		{"account": "1122 - 應收帳款 - O", "debit": 0, "credit": 100, "reference_type": "Sales Invoice", "reference_name": "SINV-SETTLE-001"},
	]


def _split_account_preview():
	return [
		{"account": "2203 - 訂金預收款 - O", "debit": 40, "credit": 0},
		{"account": "2204 - 尾款預收款 - O", "debit": 60, "credit": 0},
		{"account": "1122 - 應收帳款 - O", "debit": 0, "credit": 100},
	]


def test_site_not_expected_blocks_without_create(monkeypatch):
	db = _fake_environment(monkeypatch, site="erpnext.localhost")
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.journal_entries == {}


def test_bad_confirmation_token_blocks_without_create(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token="BAD")
	assert report["status"] == "blocked"
	assert db.journal_entries == {}


def test_readiness_fail_blocks_without_create(monkeypatch):
	db = _fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(status="fail", ready_to_create_advance_settlement=False)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.journal_entries == {}


def test_readiness_warning_blocks_without_create(monkeypatch):
	db = _fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(status="warning", ready_to_create_advance_settlement=False)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.journal_entries == {}


def test_empty_settlement_preview_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(preview=[])
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.journal_entries == {}


def test_vehicle_missing_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles = {}
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.journal_entries == {}


def test_vehicle_formal_delivery_status_not_completed_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-SETTLE-001"].formal_delivery_status = "銷售發票草稿"
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"


def test_vehicle_sales_invoice_mismatch_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-SETTLE-001"].sales_invoice = "OTHER"
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"


def test_already_settled_submitted_journal_returns_already_settled(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-SETTLE-001"].advance_settlement_journal_entry = "JE-SETTLE-001"
	db.journal_entries["JE-SETTLE-001"] = FakeDoc(name="JE-SETTLE-001", docstatus=1)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "already_settled"
	assert report["already_settled"] is True
	assert report["created"] is False


def test_existing_linked_journal_missing_or_unsubmitted_blocks(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.vehicles["UCV-SETTLE-001"].advance_settlement_journal_entry = "JE-MISSING"
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	db.journal_entries["JE-MISSING"] = FakeDoc(name="JE-MISSING", docstatus=0)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"


def test_happy_path_creates_and_submits_journal_entry(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["created"] is True
	assert report["submitted"] is True
	assert db.journal_entries["JE-SETTLE-001"].docstatus == 1


def test_happy_path_links_vehicle_with_controlled_write(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["applied_vehicle_updates"] == {"advance_settlement_journal_entry": "JE-SETTLE-001"}
	assert db.set_value_calls == [("Used Car Vehicle", "UCV-SETTLE-001", {"advance_settlement_journal_entry": "JE-SETTLE-001"}, True)]


def test_same_advance_account_creates_two_rows(monkeypatch):
	db = _fake_environment(monkeypatch)
	service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert len(db.journal_entries["JE-SETTLE-001"].accounts) == 2


def test_different_advance_accounts_create_three_rows(monkeypatch):
	db = _fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(preview=_split_account_preview())
	service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert len(db.journal_entries["JE-SETTLE-001"].accounts) == 3


def test_unbalanced_preview_blocks_without_create(monkeypatch):
	db = _fake_environment(monkeypatch)
	FakeReadinessService.report = _readiness_report(preview=[{"account": "2203", "debit": 100, "credit": 0}, {"account": "1122", "debit": 0, "credit": 90}])
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "blocked"
	assert db.journal_entries == {}


def test_submit_exception_returns_fail_with_message(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.journal_submit_exception = "boom"
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "fail"
	assert any("boom" in error for error in report["blocking_errors"])


def test_missing_journal_gl_entry_returns_warning(monkeypatch):
	db = _fake_environment(monkeypatch)
	original_commit = db.commit

	def commit_without_gl():
		original_commit()
		db.gl_entries = []

	db.commit = commit_without_gl
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "warning"
	assert any("GL Entry" in error for error in report["blocking_errors"])


def test_outstanding_not_zero_returns_warning_without_repair(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.outstanding_after = 10
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["status"] == "warning"
	assert report["sales_invoice_outstanding_after"] == 10


def test_restricted_counts_unchanged(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	for doctype in ("Payment Entry", "Delivery Note", "Stock Entry", "Purchase Invoice", "Sales Invoice", "Sales Invoice docstatus=1"):
		assert report["count_deltas"][doctype] == 0


def test_service_does_not_call_delete_cancel_raw_sql_or_ignore_mandatory(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	assert report["submitted"] is True
	assert db.forbidden_calls == []
	assert not hasattr(db.journal_entries["JE-SETTLE-001"], "ignore_mandatory")


def test_service_does_not_modify_sales_invoice_money_flow_voucher_or_reservation(monkeypatch):
	db = _fake_environment(monkeypatch)
	before = dict(db.sales_invoices["SINV-SETTLE-001"].__dict__)
	service.GuardedAdvanceSettlementJournalQAService().run("SINV-SETTLE-001", confirmation_token=service.CONFIRMATION_TOKEN)
	after = dict(db.sales_invoices["SINV-SETTLE-001"].__dict__)
	after["outstanding_amount"] = before["outstanding_amount"]
	assert after == before


def test_unknown_controlled_write_field_still_disallowed(monkeypatch):
	_fake_environment(monkeypatch)
	try:
		controlled_write.assert_controlled_write_policy(service.ACTION, "Used Car Vehicle", ["advance_settlement_journal_entry", "formal_delivery_note"])
	except controlled_write.UsedCarControlledWriteError:
		return
	assert False, "unknown controlled write field must be blocked"
