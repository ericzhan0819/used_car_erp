from types import SimpleNamespace

from used_car_erp.used_car_erp.services import formal_sale_accounting_closure_inspector_service as service


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
		self.docs = _base_docs()
		self.forbidden_calls = []

	def exists(self, doctype, filters):
		if isinstance(filters, str):
			return filters in self.docs.get(doctype, {})
		return any(_matches(doc, filters) for doc in self.docs.get(doctype, {}).values())

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

	def count(self, doctype, filters=None):
		return len([doc for doc in self.docs.get(doctype, {}).values() if _matches(doc, filters or {})])

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


class FakeMeta:
	def __init__(self, fields):
		self.fields = set(fields)

	def has_field(self, fieldname):
		return fieldname in self.fields


class FakeFrappe:
	def __init__(self, db):
		self.db = db

	def get_doc(self, doctype, name=None):
		return self.db.docs[doctype][name]

	def get_meta(self, doctype):
		fields = {
			"Payment Entry": {"reference_name"},
			"Delivery Note": {"against_sales_invoice"},
			"Purchase Invoice": {"bill_no"},
			"Stock Entry": {"sales_invoice_no"},
			"Journal Entry": {"cheque_no", "reference_name"},
		}
		return FakeMeta(fields.get(doctype, set()))

	def whitelist(self):
		return lambda fn: fn

	def delete_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("delete_doc")
		raise AssertionError("delete_doc must not be called")


def _fake_environment(monkeypatch):
	db = FakeDB()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	return db


def _base_docs():
	return {
		"Used Car Vehicle": {"UCV-CLOSE": _vehicle()},
		"Used Car Reservation": {"RES-CLOSE": _reservation()},
		"Sales Invoice": {"SINV-CLOSE": _invoice()},
		"Customer": {"CUST-CLOSE": FakeDoc(name="CUST-CLOSE")},
		"Used Car Money Flow": {
			"MF-DEP": _money_flow("MF-DEP", "訂金收款", 100000, "VD-DEP", "JE-DEP"),
			"MF-FIN": _money_flow("MF-FIN", "尾款收款", 900000, "VD-FIN", "JE-FIN"),
		},
		"Used Car Voucher Draft": {
			"VD-DEP": _voucher("VD-DEP", "MF-DEP", "JE-DEP", "CASH - O", "ADV-DEP - O", 100000),
			"VD-FIN": _voucher("VD-FIN", "MF-FIN", "JE-FIN", "BANK - O", "ADV-DEP - O", 900000),
		},
		"Journal Entry": {
			"JE-DEP": _journal_entry("JE-DEP", "CASH - O", "ADV-DEP - O", 100000),
			"JE-FIN": _journal_entry("JE-FIN", "BANK - O", "ADV-DEP - O", 900000),
			"JE-SETTLE": _settlement_journal_entry(),
		},
		"Account": {
			service.RECEIVABLE_ACCOUNT: _account(service.RECEIVABLE_ACCOUNT, "Asset"),
			service.INCOME_ACCOUNT: _account(service.INCOME_ACCOUNT, "Income"),
			service.TAX_ACCOUNT: _account(service.TAX_ACCOUNT, "Liability"),
			service.INVENTORY_ACCOUNT: _account(service.INVENTORY_ACCOUNT, "Asset"),
			service.EXPENSE_ACCOUNT: _account(service.EXPENSE_ACCOUNT, "Expense"),
			"CASH - O": _account("CASH - O", "Asset", "Cash"),
			"BANK - O": _account("BANK - O", "Asset", "Bank"),
			"ADV-DEP - O": _account("ADV-DEP - O", "Liability"),
			"COST-15-1 - O": _account("COST-15-1 - O", "Expense"),
		},
		"GL Entry": _gl_entries(),
		"Stock Ledger Entry": {
			"SLE-SINV": FakeDoc(name="SLE-SINV", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", item_code="USED-CAR-VEHICLE", warehouse="中古車庫存倉 - O", actual_qty=-1, stock_value_difference=-700000)
		},
		"Serial No": {"SER-CLOSE": FakeDoc(name="SER-CLOSE", status="Delivered", warehouse=None)},
		"Payment Entry": {},
		"Delivery Note": {},
		"Purchase Invoice": {},
		"Stock Entry": {},
	}


def _vehicle(**overrides):
	data = {
		"name": "UCV-CLOSE",
		"status": "已售出",
		"formal_delivery_status": "已完成",
		"sales_invoice": "SINV-CLOSE",
		"advance_settlement_journal_entry": "JE-SETTLE",
		"completed_reservation": "RES-CLOSE",
		"deposit_money_flow": "MF-DEP",
		"deposit_voucher_draft": "VD-DEP",
		"deposit_journal_entry": "JE-DEP",
		"final_money_flow": "MF-FIN",
		"final_voucher_draft": "VD-FIN",
		"final_journal_entry": "JE-FIN",
		"purchase_price": 700000,
		"total_cost": 999999,
		"gross_margin": 123456,
		"vehicle_tax_mode": "15-1 特殊扣抵",
		"modified": "2026-06-19 22:00:00",
	}
	data.update(overrides)
	return FakeDoc(**data)


def _reservation(**overrides):
	data = {
		"name": "RES-CLOSE",
		"status": "已完成",
		"vehicle": "UCV-CLOSE",
		"customer": "CUST-CLOSE",
		"deposit_amount": 100000,
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
	item = FakeDoc(serial_no="SER-CLOSE", warehouse="中古車庫存倉 - O", income_account=service.INCOME_ACCOUNT, expense_account=service.EXPENSE_ACCOUNT)
	tax = FakeDoc(account_head=service.TAX_ACCOUNT, rate=5, included_in_print_rate=1)
	data = {
		"name": "SINV-CLOSE",
		"docstatus": 1,
		"company": service.COMPANY,
		"customer": "CUST-CLOSE",
		"update_stock": 1,
		"grand_total": 1000000,
		"outstanding_amount": 0,
		"taxes_and_charges": service.TAX_TEMPLATE,
		"items": [item],
		"taxes": [tax],
	}
	data.update(overrides)
	return FakeDoc(**data)


def _money_flow(name, flow_type, amount, voucher_draft, journal_entry, **overrides):
	data = {"name": name, "status": "已入帳", "flow_type": flow_type, "amount": amount, "vehicle": "UCV-CLOSE", "reservation": "RES-CLOSE", "customer": "CUST-CLOSE", "voucher_draft": voucher_draft, "journal_entry": journal_entry}
	data.update(overrides)
	return FakeDoc(**data)


def _voucher(name, money_flow, journal_entry, debit_account, credit_account, amount, **overrides):
	data = {"name": name, "status": "已入帳", "money_flow": money_flow, "vehicle": "UCV-CLOSE", "reservation": "RES-CLOSE", "customer": "CUST-CLOSE", "journal_entry": journal_entry, "lines": [FakeDoc(account=debit_account, debit=amount, credit=0), FakeDoc(account=credit_account, debit=0, credit=amount)]}
	data.update(overrides)
	return FakeDoc(**data)


def _journal_entry(name, debit_account, credit_account, amount, **overrides):
	data = {"name": name, "docstatus": 1, "company": service.COMPANY, "accounts": [FakeDoc(account=debit_account, debit_in_account_currency=amount, credit_in_account_currency=0), FakeDoc(account=credit_account, debit_in_account_currency=0, credit_in_account_currency=amount)]}
	data.update(overrides)
	return FakeDoc(**data)


def _settlement_journal_entry(**overrides):
	data = {"name": "JE-SETTLE", "docstatus": 1, "company": service.COMPANY, "accounts": [FakeDoc(account="ADV-DEP - O", debit_in_account_currency=1000000, credit_in_account_currency=0), FakeDoc(account=service.RECEIVABLE_ACCOUNT, debit_in_account_currency=0, credit_in_account_currency=1000000)]}
	data.update(overrides)
	return FakeDoc(**data)


def _account(name, root_type, account_type=None):
	return FakeDoc(name=name, root_type=root_type, account_type=account_type, company=service.COMPANY, is_group=0, disabled=0)


def _gl_entries():
	rows = {
		"GLE-AR": FakeDoc(name="GLE-AR", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account=service.RECEIVABLE_ACCOUNT, debit=1000000, credit=0),
		"GLE-INCOME": FakeDoc(name="GLE-INCOME", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account=service.INCOME_ACCOUNT, debit=0, credit=950000),
		"GLE-TAX": FakeDoc(name="GLE-TAX", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account=service.TAX_ACCOUNT, debit=0, credit=50000),
		"GLE-COGS": FakeDoc(name="GLE-COGS", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account=service.EXPENSE_ACCOUNT, debit=700000, credit=0),
		"GLE-INV": FakeDoc(name="GLE-INV", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account=service.INVENTORY_ACCOUNT, debit=0, credit=700000),
		"GLE-DEP-DR": FakeDoc(name="GLE-DEP-DR", voucher_type="Journal Entry", voucher_no="JE-DEP", account="CASH - O", debit=100000, credit=0),
		"GLE-DEP-CR": FakeDoc(name="GLE-DEP-CR", voucher_type="Journal Entry", voucher_no="JE-DEP", account="ADV-DEP - O", debit=0, credit=100000),
		"GLE-FIN-DR": FakeDoc(name="GLE-FIN-DR", voucher_type="Journal Entry", voucher_no="JE-FIN", account="BANK - O", debit=900000, credit=0),
		"GLE-FIN-CR": FakeDoc(name="GLE-FIN-CR", voucher_type="Journal Entry", voucher_no="JE-FIN", account="ADV-DEP - O", debit=0, credit=900000),
		"GLE-SET-DR": FakeDoc(name="GLE-SET-DR", voucher_type="Journal Entry", voucher_no="JE-SETTLE", account="ADV-DEP - O", debit=1000000, credit=0),
		"GLE-SET-CR": FakeDoc(name="GLE-SET-CR", voucher_type="Journal Entry", voucher_no="JE-SETTLE", account=service.RECEIVABLE_ACCOUNT, debit=0, credit=1000000),
	}
	return rows


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
	return service.FormalSaleAccountingClosureInspectorService().run(sales_invoice="SINV-CLOSE")


def test_target_not_found_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"] = {}
	report = service.FormalSaleAccountingClosureInspectorService().run()
	assert report["status"] == "fail"
	assert any("找不到" in error for error in report["blocking_errors"])


def test_vehicle_status_not_sold_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].status = "保留中"
	assert any("status 必須是 已售出" in error for error in _run()["blocking_errors"])


def test_formal_delivery_status_not_completed_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].formal_delivery_status = "銷售發票草稿"
	assert any("formal_delivery_status 必須是 已完成" in error for error in _run()["blocking_errors"])


def test_sales_invoice_docstatus_not_submitted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-CLOSE"].docstatus = 0
	assert any("Sales Invoice docstatus 必須是 1" in error for error in _run()["blocking_errors"])


def test_sales_invoice_outstanding_not_zero_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-CLOSE"].outstanding_amount = 10
	assert any("outstanding_amount 必須為 0" in error for error in _run()["blocking_errors"])


def test_sales_invoice_gl_entry_missing_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["GL Entry"] = {name: row for name, row in db.docs["GL Entry"].items() if row.voucher_type != "Sales Invoice"}
	assert any("Sales Invoice 對應 GL Entry" in error for error in _run()["blocking_errors"])


def test_sales_invoice_sle_missing_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Stock Ledger Entry"] = {}
	assert any("Stock Ledger Entry" in error for error in _run()["blocking_errors"])


def test_sales_invoice_gl_accounts_missing_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["GL Entry"].pop("GLE-TAX")
	assert any(service.TAX_ACCOUNT in error for error in _run()["blocking_errors"])


def test_sales_invoice_gl_unbalanced_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["GL Entry"]["GLE-AR"].debit = 100
	assert any("Sales Invoice GL Entry debit / credit 不平" in error for error in _run()["blocking_errors"])


def test_settlement_je_missing_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Journal Entry"].pop("JE-SETTLE")
	assert any("Advance Settlement Journal Entry 不存在" in error for error in _run()["blocking_errors"])


def test_settlement_je_docstatus_not_submitted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Journal Entry"]["JE-SETTLE"].docstatus = 0
	assert any("Advance Settlement Journal Entry docstatus 必須是 1" in error for error in _run()["blocking_errors"])


def test_settlement_je_gl_entry_missing_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["GL Entry"] = {name: row for name, row in db.docs["GL Entry"].items() if row.voucher_no != "JE-SETTLE"}
	assert any("Advance Settlement Journal Entry 對應 GL Entry" in error for error in _run()["blocking_errors"])


def test_settlement_je_gl_unbalanced_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["GL Entry"]["GLE-SET-DR"].debit = 999
	assert any("Advance Settlement Journal Entry GL debit / credit 不平" in error for error in _run()["blocking_errors"])


def test_settlement_amount_not_equal_sales_invoice_grand_total_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-CLOSE"].grand_total = 999
	assert any("Sales Invoice grand_total" in error for error in _run()["blocking_errors"])


def test_settlement_amount_not_equal_deposit_plus_final_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Money Flow"]["MF-FIN"].amount = 800000
	assert any("deposit amount + final amount" in error for error in _run()["blocking_errors"])


def test_missing_completed_reservation_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].completed_reservation = None
	assert any("completed_reservation" in error for error in _run()["blocking_errors"])


def test_reservation_status_not_completed_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Reservation"]["RES-CLOSE"].status = "有效"
	assert any("completed_reservation 狀態必須是 已完成" in error for error in _run()["blocking_errors"])


def test_missing_deposit_or_final_money_flow_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].deposit_money_flow = None
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].final_money_flow = "MISSING"
	report = _run()
	assert any("缺少訂金金流" in error for error in report["blocking_errors"])
	assert any("尾款金流不存在" in error for error in report["blocking_errors"])


def test_money_flow_status_not_posted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Money Flow"]["MF-DEP"].status = "待審核"
	assert any("金流 status 必須是 已入帳" in error for error in _run()["blocking_errors"])


def test_missing_voucher_draft_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].deposit_voucher_draft = None
	assert any("缺少訂金傳票草稿" in error for error in _run()["blocking_errors"])


def test_voucher_draft_status_not_posted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Voucher Draft"]["VD-DEP"].status = "待審核"
	assert any("傳票草稿 status 必須是 已入帳" in error for error in _run()["blocking_errors"])


def test_missing_deposit_or_final_journal_entry_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].deposit_journal_entry = None
	assert any("缺少訂金 Journal Entry" in error for error in _run()["blocking_errors"])


def test_deposit_or_final_journal_entry_docstatus_not_submitted_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Journal Entry"]["JE-DEP"].docstatus = 0
	assert any("訂金 Journal Entry docstatus 必須是 1" in error for error in _run()["blocking_errors"])


def test_payment_entry_linked_to_target_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Payment Entry"]["PE-1"] = FakeDoc(name="PE-1", reference_name="SINV-CLOSE")
	assert any("Payment Entry" in error for error in _run()["blocking_errors"])


def test_delivery_note_linked_to_target_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Delivery Note"]["DN-1"] = FakeDoc(name="DN-1", against_sales_invoice="SINV-CLOSE")
	assert any("Delivery Note" in error for error in _run()["blocking_errors"])


def test_purchase_invoice_linked_to_target_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Purchase Invoice"]["PINV-1"] = FakeDoc(name="PINV-1", bill_no="SINV-CLOSE")
	assert any("Purchase Invoice" in error for error in _run()["blocking_errors"])


def test_happy_path_passes_closed_and_ready(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["status"] == "pass"
	assert report["closed"] is True
	assert report["ready_for_ui_review"] is True
	assert report["amount_summary"]["advance_total"] == 1000000


def test_service_does_not_call_writing_methods(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = _run()
	assert report["status"] == "pass"
	assert db.forbidden_calls == []
	assert list(report.keys()) == list(service.REPORT_KEYS)


def test_candidate_finder_only_returns_closed_target(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-DRAFT"] = _vehicle(name="UCV-DRAFT", sales_invoice="SINV-DRAFT", modified="2026-06-19 23:00:00")
	db.docs["Sales Invoice"]["SINV-DRAFT"] = _invoice(name="SINV-DRAFT", docstatus=0)
	db.docs["Used Car Vehicle"]["UCV-NO-SETTLE"] = _vehicle(name="UCV-NO-SETTLE", sales_invoice="SINV-NO-SETTLE", advance_settlement_journal_entry=None, modified="2026-06-19 23:10:00")
	db.docs["Sales Invoice"]["SINV-NO-SETTLE"] = _invoice(name="SINV-NO-SETTLE")
	rows = service.find_formal_sale_accounting_closure_candidates(limit=10)
	assert [row["vehicle"] for row in rows] == ["UCV-CLOSE"]


def test_15_1_and_cost_fields_do_not_affect_closure_amount(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].purchase_price = 123
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].total_cost = 9999999
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].gross_margin = -999999
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].vehicle_tax_mode = "15-1 特殊扣抵"
	report = _run()
	assert report["status"] == "pass"
	assert report["advance_total"] == 1000000
	assert report["amount_summary"]["purchase_price"] == 123
