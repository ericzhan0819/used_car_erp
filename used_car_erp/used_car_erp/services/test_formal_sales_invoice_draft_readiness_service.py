from types import SimpleNamespace

from used_car_erp.used_car_erp.services import formal_sales_invoice_draft_readiness_service as service


class UnsafeDoc(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)

	def insert(self):
		raise AssertionError("insert must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def submit(self):
		raise AssertionError("submit must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")


class FakeMeta:
	def __init__(self, fields):
		self.fields = set(fields)

	def has_field(self, fieldname):
		return fieldname in self.fields


class FakeDefaults:
	def get_user_default(self, key):
		return service.COMPANY if key == "Company" else None

	def get_global_default(self, key):
		return service.COMPANY if key == "company" else None


class FakeDB:
	def __init__(self):
		self.docs = {}
		self.stock_entry_details = {}

	def exists(self, doctype, filters):
		if isinstance(filters, str):
			return filters in self.docs.get(doctype, {})
		if isinstance(filters, dict):
			return any(_matches(doc, filters) for doc in self.docs.get(doctype, {}).values())
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		if doctype == "Stock Entry Detail":
			for row in self.stock_entry_details.values():
				if _matches(row, filters):
					return row.get(fieldname)
		for doc in self.docs.get(doctype, {}).values():
			if _matches(doc, filters):
				return doc.get(fieldname)
		return None

	def get_all(self, doctype, filters=None, fields=None, order_by=None, limit=None):
		rows = [doc for doc in self.docs.get(doctype, {}).values() if _matches(doc, filters or {})]
		rows.sort(key=lambda doc: doc.get("modified") or "", reverse=True)
		return [_project(doc, fields) for doc in rows[: int(limit or len(rows))]]

	def set_value(self, *args, **kwargs):
		raise AssertionError("set_value must not be called")

	def commit(self):
		raise AssertionError("commit must not be called")

	def rollback(self):
		raise AssertionError("rollback must not be called")


class FakeFrappe:
	def __init__(self, db):
		self.db = db
		self.defaults = FakeDefaults()

	def get_doc(self, doctype, name=None):
		return self.db.docs[doctype][name]

	def get_meta(self, doctype):
		if doctype == "Used Car Vehicle":
			return FakeMeta(("company", "warehouse", "target_warehouse", "source_warehouse", "stock_warehouse"))
		return FakeMeta(())

	def whitelist(self):
		return lambda fn: fn


def _matches(doc, filters):
	for key, expected in filters.items():
		actual = doc.get(key)
		if isinstance(expected, list):
			operator = expected[0]
			value = expected[1] if len(expected) > 1 else None
			if operator == "is" and value == "not set" and actual:
				return False
			if operator == "is" and value == "set" and not actual:
				return False
			if operator == "!=" and actual == value:
				return False
			if operator == "like" and str(value).replace("%", "") not in str(actual or ""):
				return False
			continue
		if actual != expected:
			return False
	return True


def _project(doc, fields):
	row = {}
	for field in fields or ():
		if " as " in field:
			source, target = field.split(" as ", 1)
			row[target] = doc.get(source)
		else:
			row[field] = doc.get(field)
	return row


def _fake_environment(monkeypatch):
	db = FakeDB()
	db.docs = {
		"Used Car Vehicle": {"UCV-READY": _vehicle()},
		"Used Car Reservation": {"RES-READY": _reservation()},
		"Customer": {"CUST-READY": UnsafeDoc(name="CUST-READY")},
		"Item": {"ITEM-READY": _item()},
		"Item Group": {},
		"Company": {service.COMPANY: UnsafeDoc(name=service.COMPANY, default_income_account=None)},
		"Warehouse": {"WH-READY - O": UnsafeDoc(name="WH-READY - O", company=service.COMPANY, is_group=0, disabled=0)},
		"Account": {
			"INC-READY - O": _account("INC-READY - O"),
			service.SALES_TAX_ACCOUNT: _account(service.SALES_TAX_ACCOUNT),
		},
		"Used Car Money Flow": {
			"MF-DEP": UnsafeDoc(name="MF-DEP", status="已入帳", flow_type="訂金收款", amount=100000),
			"MF-FIN": UnsafeDoc(name="MF-FIN", status="已入帳", flow_type="尾款收款", amount=900000),
		},
		"Used Car Voucher Draft": {
			"VD-DEP": UnsafeDoc(name="VD-DEP", status="已入帳", journal_entry="JE-DEP"),
			"VD-FIN": UnsafeDoc(name="VD-FIN", status="已入帳", journal_entry="JE-FIN"),
		},
		"Journal Entry": {
			"JE-DEP": UnsafeDoc(name="JE-DEP", docstatus=1),
			"JE-FIN": UnsafeDoc(name="JE-FIN", docstatus=1),
		},
		"Sales Taxes and Charges Template": {service.SALES_TAX_TEMPLATE: _tax_template()},
	}
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	return db


def _vehicle(**overrides):
	data = {
		"name": "UCV-READY",
		"status": "已售出",
		"company": service.COMPANY,
		"formal_delivery_status": None,
		"sales_invoice": None,
		"completed_reservation": "RES-READY",
		"customer": "CUST-READY",
		"item": "ITEM-READY",
		"serial_no": "VIN-READY",
		"stock_warehouse": "WH-READY - O",
		"deposit_money_flow": "MF-DEP",
		"deposit_voucher_draft": "VD-DEP",
		"deposit_journal_entry": "JE-DEP",
		"final_money_flow": "MF-FIN",
		"final_voucher_draft": "VD-FIN",
		"final_journal_entry": "JE-FIN",
		"purchase_document_type": "統一發票",
		"modified": "2026-06-19 12:00:00",
	}
	data.update(overrides)
	return UnsafeDoc(**data)


def _reservation(**overrides):
	data = {
		"name": "RES-READY",
		"vehicle": "UCV-READY",
		"status": "已完成",
		"customer": "CUST-READY",
		"deposit_amount": 100000,
		"final_payment_amount": 900000,
		"money_flow": "MF-DEP",
		"voucher_draft": "VD-DEP",
		"journal_entry": "JE-DEP",
		"final_money_flow": "MF-FIN",
		"final_voucher_draft": "VD-FIN",
		"final_journal_entry": "JE-FIN",
	}
	data.update(overrides)
	return UnsafeDoc(**data)


def _item(income_account="INC-READY - O"):
	return UnsafeDoc(
		name="ITEM-READY",
		item_group=None,
		item_defaults=[UnsafeDoc(company=service.COMPANY, income_account=income_account)],
	)


def _account(name):
	return UnsafeDoc(name=name, company=service.COMPANY, is_group=0, disabled=0)


def _tax_template(**overrides):
	data = {
		"name": service.SALES_TAX_TEMPLATE,
		"company": service.COMPANY,
		"disabled": 0,
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


def _run(db, vehicle="UCV-READY"):
	return service.FormalSalesInvoiceDraftReadinessService().run(vehicle_name=vehicle)


def test_complete_ready_vehicle_passes(monkeypatch):
	db = _fake_environment(monkeypatch)

	report = _run(db)

	assert report["status"] == "pass"
	assert report["ready_to_create_sales_invoice_draft"] is True
	assert report["sales_amount"] == 1000000
	assert report["income_account"] == "INC-READY - O"


def test_missing_vehicle_fails(monkeypatch):
	db = _fake_environment(monkeypatch)

	report = _run(db, "MISSING")

	assert report["status"] == "fail"
	assert any("Used Car Vehicle 不存在" in error for error in report["blocking_errors"])


def test_vehicle_not_sold_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].status = "上架中"

	report = _run(db)

	assert any("狀態必須是已售出" in error for error in report["blocking_errors"])


def test_existing_sales_invoice_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].sales_invoice = "SINV-EXISTS"

	report = _run(db)

	assert any("不可重複建立" in error for error in report["blocking_errors"])


def test_completed_formal_delivery_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].formal_delivery_status = "已完成"

	report = _run(db)

	assert any("已完成正式交車入帳" in error for error in report["blocking_errors"])


def test_missing_completed_reservation_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].completed_reservation = None
	db.docs["Used Car Reservation"] = {}

	report = _run(db)

	assert "找不到已完成保留單。" in report["blocking_errors"]


def test_reservation_not_completed_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Reservation"]["RES-READY"].status = "有效"

	report = _run(db)

	assert any("保留單狀態必須是已完成" in error for error in report["blocking_errors"])


def test_missing_customer_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Reservation"]["RES-READY"].customer = None

	report = _run(db)

	assert any("缺少 Customer" in error for error in report["blocking_errors"])


def test_missing_item_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].item = None

	report = _run(db)

	assert "車輛尚未建立 Item。" in report["blocking_errors"]


def test_missing_serial_no_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].serial_no = None

	report = _run(db)

	assert "車輛尚未建立 Serial No。" in report["blocking_errors"]


def test_missing_warehouse_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].stock_warehouse = None

	report = _run(db)

	assert any("找不到車輛庫存倉" in error for error in report["blocking_errors"])


def test_unposted_money_flow_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Money Flow"]["MF-DEP"].status = "待入帳"
	db.docs["Used Car Money Flow"]["MF-FIN"].status = "待入帳"

	report = _run(db)

	assert any("金流尚未入帳" in error for error in report["blocking_errors"])


def test_unposted_or_missing_journal_voucher_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Voucher Draft"]["VD-DEP"].status = "待審核"
	db.docs["Used Car Voucher Draft"]["VD-FIN"].journal_entry = None

	report = _run(db)

	assert any("傳票草稿尚未入帳" in error for error in report["blocking_errors"])
	assert any("傳票草稿缺少正式會計傳票" in error for error in report["blocking_errors"])


def test_voucher_journal_mismatch_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Voucher Draft"]["VD-DEP"].journal_entry = "JE-OTHER"

	report = _run(db)

	assert any("未連結車輛成交摘要" in error for error in report["blocking_errors"])


def test_pending_purchase_document_type_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-READY"].purchase_document_type = None

	report = _run(db)

	assert any("買入憑證尚待會計確認" in error for error in report["blocking_errors"])


def test_bad_tax_template_or_tax_account_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Sales Taxes and Charges Template"][service.SALES_TAX_TEMPLATE].taxes[0].account_head = "BAD-TAX"
	db.docs["Account"][service.SALES_TAX_ACCOUNT].disabled = 1

	report = _run(db)

	assert any("account_head 必須是" in error for error in report["blocking_errors"])
	assert any("已停用" in error for error in report["blocking_errors"])


def test_candidate_finder_filters_ready_targets(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-INVOICE"] = _vehicle(name="UCV-INVOICE", sales_invoice="SINV-1")
	db.docs["Used Car Vehicle"]["UCV-DONE"] = _vehicle(name="UCV-DONE", formal_delivery_status="已完成")
	db.docs["Used Car Vehicle"]["UCV-LISTED"] = _vehicle(name="UCV-LISTED", status="上架中")

	rows = service.find_formal_sales_invoice_draft_readiness_candidates(limit=10)

	assert [row["vehicle"] for row in rows] == ["UCV-READY"]
	assert set(rows[0]) >= {
		"vehicle",
		"vehicle_status",
		"formal_delivery_status",
		"sales_invoice",
		"completed_reservation",
		"customer",
		"item",
		"serial_no",
		"stock_warehouse",
		"deposit_money_flow",
		"deposit_voucher_draft",
		"deposit_journal_entry",
		"final_money_flow",
		"final_voucher_draft",
		"final_journal_entry",
		"modified",
	}


def test_readiness_service_does_not_call_writing_methods(monkeypatch):
	db = _fake_environment(monkeypatch)

	report = _run(db)

	assert report["status"] == "pass"
	assert list(report.keys()) == list(service.REPORT_KEYS)
