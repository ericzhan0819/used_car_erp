from types import SimpleNamespace

from used_car_erp.used_car_erp.services import advance_settlement_readiness_service as service


class FakeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def insert(self):
		raise AssertionError("insert must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")

	def submit(self):
		raise AssertionError("submit must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")


class FakeDB:
	def __init__(self):
		self.docs = {
			"Used Car Vehicle": {"UCV-SETTLE": _vehicle()},
			"Used Car Reservation": {"RES-SETTLE": _reservation()},
			"Sales Invoice": {"SINV-SETTLE": _invoice()},
			"Customer": {"CUST-SETTLE": FakeDoc(name="CUST-SETTLE")},
			"Used Car Money Flow": {
				"MF-DEP": _money_flow("MF-DEP", "訂金收款", 100000, "VD-DEP", "JE-DEP"),
				"MF-FIN": _money_flow("MF-FIN", "尾款收款", 900000, "VD-FIN", "JE-FIN"),
			},
			"Used Car Voucher Draft": {
				"VD-DEP": _voucher("VD-DEP", "MF-DEP", "JE-DEP", service.RECEIVABLE_ACCOUNT, "ADV-DEP - O", 100000),
				"VD-FIN": _voucher("VD-FIN", "MF-FIN", "JE-FIN", service.RECEIVABLE_ACCOUNT, "ADV-DEP - O", 900000),
			},
			"Journal Entry": {
				"JE-DEP": _journal_entry("JE-DEP", "CASH - O", "ADV-DEP - O", 100000),
				"JE-FIN": _journal_entry("JE-FIN", "BANK - O", "ADV-DEP - O", 900000),
			},
			"Account": {
				service.RECEIVABLE_ACCOUNT: _account(service.RECEIVABLE_ACCOUNT, "Asset"),
				"CASH - O": _account("CASH - O", "Asset", "Cash"),
				"BANK - O": _account("BANK - O", "Asset", "Bank"),
				"ADV-DEP - O": _account("ADV-DEP - O", "Liability"),
				"ADV-FIN - O": _account("ADV-FIN - O", "Liability"),
				"COST-15-1 - O": _account("COST-15-1 - O", "Expense"),
			},
			"GL Entry": {
				"GLE-AR": FakeDoc(
					name="GLE-AR",
					voucher_type="Sales Invoice",
					voucher_no="SINV-SETTLE",
					account=service.RECEIVABLE_ACCOUNT,
					debit=1000000,
					credit=0,
				)
			},
		}
		self.forbidden_calls = []

	def exists(self, doctype, filters):
		if isinstance(filters, str):
			return filters in self.docs.get(doctype, {})
		if isinstance(filters, dict):
			return any(_matches(doc, filters) for doc in self.docs.get(doctype, {}).values())
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		if isinstance(filters, str):
			doc = self.docs.get(doctype, {}).get(filters)
			return doc.get(fieldname) if doc else None
		for doc in self.docs.get(doctype, {}).values():
			if _matches(doc, filters):
				return doc.get(fieldname)
		return None

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

	def rollback(self):
		self.forbidden_calls.append("rollback")
		raise AssertionError("rollback must not be called")

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


def _fake_environment(monkeypatch):
	db = FakeDB()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	return db


def _vehicle(**overrides):
	data = {
		"name": "UCV-SETTLE",
		"status": "已售出",
		"formal_delivery_status": "已完成",
		"sales_invoice": "SINV-SETTLE",
		"advance_settlement_journal_entry": None,
		"completed_reservation": "RES-SETTLE",
		"deposit_money_flow": "MF-DEP",
		"deposit_voucher_draft": "VD-DEP",
		"deposit_journal_entry": "JE-DEP",
		"final_money_flow": "MF-FIN",
		"final_voucher_draft": "VD-FIN",
		"final_journal_entry": "JE-FIN",
		"total_cost": 999999,
		"gross_margin": 123456,
		"vehicle_tax_mode": "15-1 特殊扣抵",
		"modified": "2026-06-19 20:00:00",
	}
	data.update(overrides)
	return FakeDoc(**data)


def _reservation(**overrides):
	data = {
		"name": "RES-SETTLE",
		"status": "已完成",
		"vehicle": "UCV-SETTLE",
		"customer": "CUST-SETTLE",
		"money_flow": "MF-DEP",
		"voucher_draft": "VD-DEP",
		"journal_entry": "JE-DEP",
		"final_money_flow": "MF-FIN",
		"final_voucher_draft": "VD-FIN",
		"final_journal_entry": "JE-FIN",
	}
	data.update(overrides)
	return FakeDoc(**data)


def _invoice(**overrides):
	data = {
		"name": "SINV-SETTLE",
		"docstatus": 1,
		"company": service.COMPANY,
		"customer": "CUST-SETTLE",
		"debit_to": service.RECEIVABLE_ACCOUNT,
		"grand_total": 1000000,
		"outstanding_amount": 1000000,
	}
	data.update(overrides)
	return FakeDoc(**data)


def _money_flow(name, flow_type, amount, voucher_draft, journal_entry, **overrides):
	data = {
		"name": name,
		"status": "已入帳",
		"flow_type": flow_type,
		"amount": amount,
		"vehicle": "UCV-SETTLE",
		"reservation": "RES-SETTLE",
		"customer": "CUST-SETTLE",
		"voucher_draft": voucher_draft,
		"journal_entry": journal_entry,
	}
	data.update(overrides)
	return FakeDoc(**data)


def _voucher(name, money_flow, journal_entry, debit_account, credit_account, amount, **overrides):
	data = {
		"name": name,
		"status": "已入帳",
		"money_flow": money_flow,
		"vehicle": "UCV-SETTLE",
		"reservation": "RES-SETTLE",
		"customer": "CUST-SETTLE",
		"journal_entry": journal_entry,
		"lines": [
			FakeDoc(account=debit_account, debit=amount, credit=0),
			FakeDoc(account=credit_account, debit=0, credit=amount),
		],
	}
	data.update(overrides)
	return FakeDoc(**data)


def _journal_entry(name, debit_account, credit_account, amount, **overrides):
	data = {
		"name": name,
		"docstatus": 1,
		"company": service.COMPANY,
		"accounts": [
			FakeDoc(account=debit_account, debit_in_account_currency=amount, credit_in_account_currency=0),
			FakeDoc(account=credit_account, debit_in_account_currency=0, credit_in_account_currency=amount),
		],
	}
	data.update(overrides)
	return FakeDoc(**data)


def _account(name, root_type, account_type=None):
	return FakeDoc(name=name, root_type=root_type, account_type=account_type, company=service.COMPANY, is_group=0, disabled=0)


def _matches(doc, filters):
	for key, expected in filters.items():
		actual = doc.get(key)
		if isinstance(expected, list):
			operator = expected[0]
			value = expected[1] if len(expected) > 1 else None
			if operator == "is" and value == "set" and not actual:
				return False
			if operator == "is" and value == "not set" and actual:
				return False
			if operator == "!=" and actual == value:
				return False
			continue
		if actual != expected:
			return False
	return True


def _project(doc, fields):
	return {field: doc.get(field) for field in fields or ()}


def _run():
	return service.AdvanceSettlementReadinessService().run(sales_invoice="SINV-SETTLE")


def test_candidate_not_found_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"] = {}
	report = service.AdvanceSettlementReadinessService().run()
	assert report["status"] == "fail"
	assert any("找不到" in error for error in report["blocking_errors"])


def test_vehicle_status_not_sold_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].status = "保留中"
	assert any("status 必須是 已售出" in error for error in _run()["blocking_errors"])


def test_formal_delivery_status_not_completed_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].formal_delivery_status = "銷售發票草稿"
	assert any("formal_delivery_status 必須是 已完成" in error for error in _run()["blocking_errors"])


def test_sales_invoice_docstatus_not_submitted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-SETTLE"].docstatus = 0
	assert any("docstatus 必須是 1" in error for error in _run()["blocking_errors"])


def test_vehicle_sales_invoice_mismatch_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].sales_invoice = "OTHER"
	assert _run()["status"] == "fail"


def test_existing_advance_settlement_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].advance_settlement_journal_entry = "JE-ADV"
	assert any("advance_settlement_journal_entry" in error for error in _run()["blocking_errors"])


def test_missing_completed_reservation_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].completed_reservation = None
	assert any("completed_reservation" in error for error in _run()["blocking_errors"])


def test_missing_deposit_or_final_money_flow_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].deposit_money_flow = None
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].final_money_flow = "MISSING"
	report = _run()
	assert any("缺少訂金金流" in error for error in report["blocking_errors"])
	assert any("尾款金流不存在" in error for error in report["blocking_errors"])


def test_money_flow_status_not_posted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Money Flow"]["MF-DEP"].status = "待審核"
	assert any("金流 status 必須是 已入帳" in error for error in _run()["blocking_errors"])


def test_missing_voucher_draft_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].deposit_voucher_draft = None
	assert any("缺少訂金傳票草稿" in error for error in _run()["blocking_errors"])


def test_voucher_draft_status_not_posted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Voucher Draft"]["VD-DEP"].status = "待審核"
	assert any("傳票草稿 status 必須是 已入帳" in error for error in _run()["blocking_errors"])


def test_missing_journal_entry_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].deposit_journal_entry = None
	assert any("缺少訂金 Journal Entry" in error for error in _run()["blocking_errors"])


def test_journal_entry_docstatus_not_submitted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Journal Entry"]["JE-DEP"].docstatus = 0
	assert any("Journal Entry docstatus 必須是 1" in error for error in _run()["blocking_errors"])


def test_journal_entry_unbalanced_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Journal Entry"]["JE-DEP"].accounts[1].credit_in_account_currency = 999
	assert any("debit / credit 不平" in error for error in _run()["blocking_errors"])


def test_unresolved_advance_liability_account_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Voucher Draft"]["VD-DEP"].lines[1].account = "COST-15-1 - O"
	db.docs["Journal Entry"]["JE-DEP"].accounts[1].account = "COST-15-1 - O"
	assert any("無法解析預收" in error for error in _run()["blocking_errors"])


def test_unresolved_receivable_account_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-SETTLE"].debit_to = None
	db.docs["Account"].pop(service.RECEIVABLE_ACCOUNT)
	db.docs["GL Entry"] = {}
	assert any("receivable account" in error or "GL Entry" in error for error in _run()["blocking_errors"])


def test_advance_total_equals_grand_total_passes(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["status"] == "pass"
	assert report["ready_to_create_advance_settlement"] is True
	assert report["advance_total"] == 1000000


def test_advance_total_less_than_grand_total_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-SETTLE"].grand_total = 1100000
	assert any("小於" in error for error in _run()["blocking_errors"])


def test_advance_total_greater_than_grand_total_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-SETTLE"].grand_total = 900000
	assert any("大於" in error for error in _run()["blocking_errors"])


def test_same_advance_account_preview_merges_debit(monkeypatch):
	_fake_environment(monkeypatch)
	preview = _run()["settlement_preview"]
	assert len([row for row in preview if row["debit"] > 0]) == 1
	assert preview[0]["debit"] == 1000000
	assert preview[-1]["credit"] == 1000000


def test_different_advance_accounts_preview_splits_debit(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Voucher Draft"]["VD-FIN"].lines[1].account = "ADV-FIN - O"
	db.docs["Journal Entry"]["JE-FIN"].accounts[1].account = "ADV-FIN - O"
	preview = _run()["settlement_preview"]
	assert len([row for row in preview if row["debit"] > 0]) == 2
	assert {row["account"] for row in preview if row["debit"] > 0} == {"ADV-DEP - O", "ADV-FIN - O"}


def test_service_does_not_call_writing_methods(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = _run()
	assert report["status"] == "pass"
	assert db.forbidden_calls == []
	assert list(report.keys()) == list(service.REPORT_KEYS)


def test_candidate_finder_excludes_existing_advance_settlement(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-DONE"] = _vehicle(
		name="UCV-DONE",
		sales_invoice="SINV-DONE",
		advance_settlement_journal_entry="JE-ADV",
		modified="2026-06-19 21:00:00",
	)
	db.docs["Sales Invoice"]["SINV-DONE"] = _invoice(name="SINV-DONE")
	rows = service.find_advance_settlement_readiness_candidates(limit=10)
	assert [row["vehicle"] for row in rows] == ["UCV-SETTLE"]


def test_15_1_and_cost_fields_do_not_affect_settlement_amount(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].total_cost = 9999999
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].gross_margin = -999999
	db.docs["Used Car Vehicle"]["UCV-SETTLE"].vehicle_tax_mode = "15-1 特殊扣抵"
	report = _run()
	assert report["status"] == "pass"
	assert report["advance_total"] == 1000000
	assert all(row["account"] != "COST-15-1 - O" for row in report["settlement_preview"])
