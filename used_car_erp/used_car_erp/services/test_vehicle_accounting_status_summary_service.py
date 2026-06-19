from types import SimpleNamespace

from used_car_erp.used_car_erp.services import vehicle_accounting_status_summary_service as service


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
	fake = FakeFrappe(db)
	monkeypatch.setattr(service, "frappe", fake)
	monkeypatch.setattr(service.FormalSaleAccountingClosureInspectorService.__module__, "frappe", fake, raising=False)
	import used_car_erp.used_car_erp.services.formal_sale_accounting_closure_inspector_service as closure_service

	monkeypatch.setattr(closure_service, "frappe", fake)
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
			"1102-UC - 應收帳款 - O": _account("1102-UC - 應收帳款 - O", "Asset"),
			"4110-UC - 中古車銷貨收入 - O": _account("4110-UC - 中古車銷貨收入 - O", "Income"),
			"0202134 - 銷項稅額 - O": _account("0202134 - 銷項稅額 - O", "Liability"),
			"1211 - 中古車庫存 - O": _account("1211 - 中古車庫存 - O", "Asset"),
			"0100005-UC - 中古車銷貨成本 - O": _account("0100005-UC - 中古車銷貨成本 - O", "Expense"),
			"CASH - O": _account("CASH - O", "Asset", "Cash"),
			"BANK - O": _account("BANK - O", "Asset", "Bank"),
			"ADV-DEP - O": _account("ADV-DEP - O", "Liability"),
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
		"customer": "CUST-CLOSE",
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
		"modified": "2026-06-19 22:00:00",
	}
	data.update(overrides)
	return FakeDoc(**data)


def _reservation(**overrides):
	data = {"name": "RES-CLOSE", "status": "已完成", "vehicle": "UCV-CLOSE", "customer": "CUST-CLOSE", "money_flow": "MF-DEP", "voucher_draft": "VD-DEP", "journal_entry": "JE-DEP", "final_money_flow": "MF-FIN", "final_voucher_draft": "VD-FIN", "final_journal_entry": "JE-FIN"}
	data.update(overrides)
	return FakeDoc(**data)


def _invoice(**overrides):
	item = FakeDoc(serial_no="SER-CLOSE", warehouse="中古車庫存倉 - O", income_account="4110-UC - 中古車銷貨收入 - O", expense_account="0100005-UC - 中古車銷貨成本 - O")
	tax = FakeDoc(account_head="0202134 - 銷項稅額 - O", rate=5, included_in_print_rate=1)
	data = {"name": "SINV-CLOSE", "docstatus": 1, "company": "OO", "customer": "CUST-CLOSE", "update_stock": 1, "grand_total": 1000000, "outstanding_amount": 0, "taxes_and_charges": "台灣營業稅 5%（含稅） - O", "items": [item], "taxes": [tax], "remarks": "formal"}
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
	data = {"name": name, "docstatus": 1, "company": "OO", "accounts": [FakeDoc(account=debit_account, debit_in_account_currency=amount, credit_in_account_currency=0), FakeDoc(account=credit_account, debit_in_account_currency=0, credit_in_account_currency=amount)]}
	data.update(overrides)
	return FakeDoc(**data)


def _settlement_journal_entry(**overrides):
	data = {"name": "JE-SETTLE", "docstatus": 1, "company": "OO", "accounts": [FakeDoc(account="ADV-DEP - O", debit_in_account_currency=1000000, credit_in_account_currency=0), FakeDoc(account="1102-UC - 應收帳款 - O", debit_in_account_currency=0, credit_in_account_currency=1000000)]}
	data.update(overrides)
	return FakeDoc(**data)


def _account(name, root_type, account_type=None):
	return FakeDoc(name=name, root_type=root_type, account_type=account_type, company="OO", is_group=0, disabled=0)


def _gl_entries():
	return {
		"GLE-AR": FakeDoc(name="GLE-AR", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account="1102-UC - 應收帳款 - O", debit=1000000, credit=0),
		"GLE-INCOME": FakeDoc(name="GLE-INCOME", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account="4110-UC - 中古車銷貨收入 - O", debit=0, credit=950000),
		"GLE-TAX": FakeDoc(name="GLE-TAX", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account="0202134 - 銷項稅額 - O", debit=0, credit=50000),
		"GLE-COGS": FakeDoc(name="GLE-COGS", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account="0100005-UC - 中古車銷貨成本 - O", debit=700000, credit=0),
		"GLE-INV": FakeDoc(name="GLE-INV", voucher_type="Sales Invoice", voucher_no="SINV-CLOSE", account="1211 - 中古車庫存 - O", debit=0, credit=700000),
		"GLE-DEP-DR": FakeDoc(name="GLE-DEP-DR", voucher_type="Journal Entry", voucher_no="JE-DEP", account="CASH - O", debit=100000, credit=0),
		"GLE-DEP-CR": FakeDoc(name="GLE-DEP-CR", voucher_type="Journal Entry", voucher_no="JE-DEP", account="ADV-DEP - O", debit=0, credit=100000),
		"GLE-FIN-DR": FakeDoc(name="GLE-FIN-DR", voucher_type="Journal Entry", voucher_no="JE-FIN", account="BANK - O", debit=900000, credit=0),
		"GLE-FIN-CR": FakeDoc(name="GLE-FIN-CR", voucher_type="Journal Entry", voucher_no="JE-FIN", account="ADV-DEP - O", debit=0, credit=900000),
		"GLE-SET-DR": FakeDoc(name="GLE-SET-DR", voucher_type="Journal Entry", voucher_no="JE-SETTLE", account="ADV-DEP - O", debit=1000000, credit=0),
		"GLE-SET-CR": FakeDoc(name="GLE-SET-CR", voucher_type="Journal Entry", voucher_no="JE-SETTLE", account="1102-UC - 應收帳款 - O", debit=0, credit=1000000),
	}


def _matches(doc, filters):
	for key, expected in filters.items():
		actual = doc.get(key)
		if isinstance(expected, list):
			operator = expected[0]
			value = expected[1] if len(expected) > 1 else None
			if operator == "in" and actual not in value:
				return False
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


def _run(**kwargs):
	return service.VehicleAccountingStatusSummaryService().run(sales_invoice="SINV-CLOSE", **kwargs)


def test_target_not_found_fails_not_ready(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"] = {}
	report = service.VehicleAccountingStatusSummaryService().run()
	assert report["status"] == "fail"
	assert report["ready_for_vehicle_page"] is False


def test_inventory_without_sale_is_not_started(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"] = _vehicle(status="庫存中", customer=None, completed_reservation=None, sales_invoice=None, advance_settlement_journal_entry=None, deposit_money_flow=None, deposit_voucher_draft=None, deposit_journal_entry=None, final_money_flow=None, final_voucher_draft=None, final_journal_entry=None)
	report = service.VehicleAccountingStatusSummaryService().run(vehicle_name="UCV-CLOSE")
	assert report["business_status"] == "未開始"


def test_reserved_or_money_flow_pending_needs_accounting_review(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].status = "保留中"
	db.docs["Sales Invoice"] = {}
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].sales_invoice = None
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].advance_settlement_journal_entry = None
	report = service.VehicleAccountingStatusSummaryService().run(vehicle_name="UCV-CLOSE")
	assert report["business_status"] == "待會計確認"


def test_sold_missing_completed_reservation_needs_business_data(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].completed_reservation = None
	report = _run()
	assert report["business_status"] == "需補資料"


def test_sales_invoice_draft_status(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-CLOSE"].docstatus = 0
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].advance_settlement_journal_entry = None
	report = _run()
	assert report["business_status"] == "已建立發票草稿"
	assert report["next_action_code"] == "submit_sales_invoice"


def test_submitted_invoice_before_formal_status_sync(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].formal_delivery_status = "銷售發票草稿"
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].advance_settlement_journal_entry = None
	report = _run()
	assert report["business_status"] == "發票已提交"
	assert report["next_action_code"] == "sync_formal_delivery_status"


def test_submitted_invoice_completed_formal_status_needs_settlement(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].advance_settlement_journal_entry = None
	report = _run()
	assert report["business_status"] == "發票已提交"
	assert report["next_action_code"] == "create_advance_settlement"


def test_settlement_submitted_but_closure_business_gate_fail_is_settled(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Money Flow"]["MF-FIN"].amount = 800000
	report = _run()
	assert report["business_status"] == "預收款已沖轉"
	assert report["next_action_code"] == "review_accounting_closure"


def test_settlement_submitted_but_accounting_blocker_is_error(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["GL Entry"] = {name: row for name, row in db.docs["GL Entry"].items() if row.voucher_no != "JE-SETTLE"}
	report = _run()
	assert report["business_status"] == "錯誤需處理"
	assert report["next_action_code"] == "review_accounting_error"


def test_closure_pass_is_closed(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["business_status"] == "會計閉環完成"
	assert report["closed"] is True
	assert report["next_action_label"] == "無下一步"


def test_linked_sales_invoice_missing_is_error(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"] = {}
	report = service.VehicleAccountingStatusSummaryService().run(vehicle_name="UCV-CLOSE")
	assert report["business_status"] == "錯誤需處理"


def test_linked_settlement_missing_is_error(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Journal Entry"].pop("JE-SETTLE")
	report = _run()
	assert report["business_status"] == "錯誤需處理"


def test_cancelled_sales_invoice_is_error(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Invoice"]["SINV-CLOSE"].docstatus = 2
	report = _run()
	assert report["business_status"] == "錯誤需處理"


def test_cancelled_journal_entry_is_error(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Journal Entry"]["JE-SETTLE"].docstatus = 2
	report = _run()
	assert report["business_status"] == "錯誤需處理"


def test_deposit_money_flow_not_posted_needs_accounting_review(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].sales_invoice = None
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].advance_settlement_journal_entry = None
	db.docs["Used Car Money Flow"]["MF-DEP"].status = "待審核"
	report = service.VehicleAccountingStatusSummaryService().run(vehicle_name="UCV-CLOSE")
	assert report["business_status"] == "待會計確認"


def test_voucher_draft_not_posted_needs_accounting_review(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].sales_invoice = None
	db.docs["Used Car Vehicle"]["UCV-CLOSE"].advance_settlement_journal_entry = None
	db.docs["Used Car Voucher Draft"]["VD-DEP"].status = "待審核"
	report = service.VehicleAccountingStatusSummaryService().run(vehicle_name="UCV-CLOSE")
	assert report["business_status"] == "待會計確認"


def test_summary_cards_include_invoice_settlement_and_closure(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert [card["label"] for card in report["summary_cards"]] == ["售車發票", "預收款沖轉", "會計閉環"]


def test_candidate_finder_returns_latest_vehicles_and_skips_qa(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-NEW"] = _vehicle(name="UCV-NEW", sales_invoice=None, advance_settlement_journal_entry=None, modified="2026-06-19 23:00:00")
	db.docs["Used Car Vehicle"]["UCV-QA"] = _vehicle(name="UCV-QA", sales_invoice="SINV-QA", modified="2026-06-19 23:30:00")
	db.docs["Sales Invoice"]["SINV-QA"] = _invoice(name="SINV-QA", remarks="P1-ACC-6E QA draft")
	rows = service.find_vehicle_accounting_status_summary_candidates(limit=10)
	assert [row["vehicle"] for row in rows] == ["UCV-NEW", "UCV-CLOSE"]
	assert db.forbidden_calls == []


def test_service_does_not_call_writing_methods(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = _run()
	assert report["status"] == "pass"
	assert db.forbidden_calls == []
	assert list(report.keys()) == list(service.REPORT_KEYS)
