from types import SimpleNamespace

from used_car_erp.used_car_erp.services import formal_sale_accounting_candidate_service as service


class FakeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def insert(self):
		raise AssertionError("insert must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def submit(self):
		raise AssertionError("submit must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")


class FakeDB:
	def __init__(self):
		self.docs = _base_docs()
		self.forbidden_calls = []

	def exists(self, doctype, name):
		return name in self.docs.get(doctype, {})

	def get_all(self, doctype, filters=None, fields=None, order_by=None, limit=None):
		rows = [doc for doc in self.docs.get(doctype, {}).values() if _matches(doc, filters or {})]
		rows.sort(key=lambda doc: doc.get("modified") or "", reverse=True)
		return [_project(doc, fields) for doc in rows[: int(limit or len(rows))]]

	def set_value(self, *args, **kwargs):
		self.forbidden_calls.append("set_value")
		raise AssertionError("set_value must not be called")

	def commit(self):
		self.forbidden_calls.append("commit")
		raise AssertionError("commit must not be called")

	def sql(self, *args, **kwargs):
		self.forbidden_calls.append("sql")
		raise AssertionError("raw SQL must not be called")


class FakeFrappe:
	def __init__(self, db):
		self.db = db

	def get_doc(self, doctype, name=None):
		return self.db.docs[doctype][name]

	def whitelist(self):
		return lambda fn: fn

	def delete_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("delete_doc")
		raise AssertionError("delete_doc must not be called")

	def rename_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("rename_doc")
		raise AssertionError("rename_doc must not be called")


def _fake_environment(monkeypatch):
	db = FakeDB()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	return db


def _base_docs():
	return {
		"Used Car Vehicle": {
			"UCV-DRAFT-SI": _vehicle("UCV-DRAFT-SI", "SINV-DRAFT", modified="2026-06-21 10:00:00"),
			"UCV-SETTLEMENT-DRAFT": _vehicle(
				"UCV-SETTLEMENT-DRAFT",
				"SINV-SUBMITTED",
				formal_delivery_status="已完成",
				modified="2026-06-21 09:00:00",
			),
			"UCV-SETTLEMENT-SUBMIT": _vehicle(
				"UCV-SETTLEMENT-SUBMIT",
				"SINV-SUBMITTED-2",
				formal_delivery_status="已完成",
				advance_settlement_journal_entry="JE-DRAFT",
				modified="2026-06-21 08:00:00",
			),
			"UCV-CANCELLED-SI": _vehicle("UCV-CANCELLED-SI", "SINV-CANCELLED", modified="2026-06-21 07:00:00"),
			"UCV-MISSING-SI": _vehicle("UCV-MISSING-SI", None, modified="2026-06-21 06:00:00"),
			"UCV-CLOSED": _vehicle(
				"UCV-CLOSED",
				"SINV-CLOSED",
				formal_delivery_status="已完成",
				advance_settlement_journal_entry="JE-SUBMITTED",
				modified="2026-06-21 05:00:00",
			),
		},
		"Sales Invoice": {
			"SINV-DRAFT": _invoice("SINV-DRAFT", 0, "Draft"),
			"SINV-SUBMITTED": _invoice("SINV-SUBMITTED", 1, "Submitted"),
			"SINV-SUBMITTED-2": _invoice("SINV-SUBMITTED-2", 1, "Submitted"),
			"SINV-CANCELLED": _invoice("SINV-CANCELLED", 2, "Cancelled"),
			"SINV-CLOSED": _invoice("SINV-CLOSED", 1, "Submitted"),
		},
		"Journal Entry": {"JE-DRAFT": _journal_entry("JE-DRAFT", 0), "JE-SUBMITTED": _journal_entry("JE-SUBMITTED", 1)},
	}


def _vehicle(name, sales_invoice, formal_delivery_status="銷售發票草稿", advance_settlement_journal_entry=None, modified="2026-06-21 00:00:00"):
	return FakeDoc(
		name=name,
		status="已售出",
		stock_no=f"STOCK-{name}",
		license_plate=f"PLATE-{name}",
		customer="CUST-001",
		sold_price=600000,
		sales_invoice=sales_invoice,
		formal_delivery_status=formal_delivery_status,
		advance_settlement_journal_entry=advance_settlement_journal_entry,
		modified=modified,
	)


def _invoice(name, docstatus, status):
	return FakeDoc(name=name, docstatus=docstatus, status=status, customer="CUST-001", grand_total=600000)


def _journal_entry(name, docstatus):
	return FakeDoc(name=name, docstatus=docstatus, status="Draft" if docstatus == 0 else "Submitted")


def _matches(doc, filters):
	for key, expected in filters.items():
		if doc.get(key) != expected:
			return False
	return True


def _project(doc, fields):
	return {field: doc.get(field) for field in fields or ()}


def _by_vehicle(report, vehicle):
	return next(row for row in report["candidates"] if row["vehicle"] == vehicle)


def test_draft_sales_invoice_needs_sales_invoice_submit(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	row = _by_vehicle(report, "UCV-DRAFT-SI")
	assert row["category"] == "needs_sales_invoice_submit"
	assert row["modified"] == "2026-06-21 10:00:00"
	assert row["route_doctype"] == "Sales Invoice"
	assert row["route_name"] == "SINV-DRAFT"


def test_candidates_are_sorted_by_category_priority(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	assert [row["category"] for row in report["candidates"]] == [
		"needs_sales_invoice_recovery",
		"blocked",
		"needs_sales_invoice_submit",
		"needs_advance_settlement_draft",
		"needs_advance_settlement_submit",
	]


def test_submitted_invoice_completed_without_settlement_needs_draft(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	row = _by_vehicle(report, "UCV-SETTLEMENT-DRAFT")
	assert row["category"] == "needs_advance_settlement_draft"
	assert row["route_doctype"] == "Used Car Vehicle"


def test_draft_advance_settlement_journal_entry_needs_submit(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	row = _by_vehicle(report, "UCV-SETTLEMENT-SUBMIT")
	assert row["category"] == "needs_advance_settlement_submit"
	assert row["route_doctype"] == "Journal Entry"
	assert row["route_name"] == "JE-DRAFT"


def test_cancelled_linked_sales_invoice_needs_recovery(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	row = _by_vehicle(report, "UCV-CANCELLED-SI")
	assert row["category"] == "needs_sales_invoice_recovery"
	assert row["route_doctype"] == "Used Car Vehicle"
	assert row["warnings"]


def test_sold_vehicle_missing_sales_invoice_is_blocked(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	row = _by_vehicle(report, "UCV-MISSING-SI")
	assert row["category"] == "blocked"
	assert "已售出車輛缺少 Sales Invoice 連結。" in row["blocking_reasons"]


def test_payload_contains_counts(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.run_formal_sale_accounting_candidates(limit=50)
	assert report["status"] == "pass"
	assert report["candidate_count"] == 5
	assert report["category_counts"] == {
		"needs_sales_invoice_recovery": 1,
		"blocked": 1,
		"needs_sales_invoice_submit": 1,
		"needs_advance_settlement_draft": 1,
		"needs_advance_settlement_submit": 1,
	}


def test_closed_formal_sale_accounting_is_excluded(monkeypatch):
	_fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	assert "UCV-CLOSED" not in [row["vehicle"] for row in report["candidates"]]
	assert report["candidate_count"] == 5
	assert report["category_counts"] == {
		"needs_sales_invoice_recovery": 1,
		"blocked": 1,
		"needs_sales_invoice_submit": 1,
		"needs_advance_settlement_draft": 1,
		"needs_advance_settlement_submit": 1,
	}


def test_service_does_not_call_write_methods(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = service.FormalSaleAccountingCandidateService().run(limit=50)
	assert report["candidate_count"] == 5
	assert db.forbidden_calls == []
