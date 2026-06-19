from types import SimpleNamespace

from used_car_erp.used_car_erp.services import submitted_sales_invoice_preflight_service as service


class FakeDB:
	def __init__(self):
		self.counts = {
			("GL Entry", (("company", service.COMPANY),)): 0,
			("Stock Ledger Entry", (("company", service.COMPANY),)): 0,
			("Sales Invoice", (("company", service.COMPANY), ("docstatus", 1))): 0,
		}
		self.sales_invoices = {}
		self.customers = {"CUST-P1-ACC-6E": True}
		self.items = {service.ITEM_CODE: _item(service.ITEM_CODE)}
		self.serial_nos = {}
		self.accounts = {name: _account(name) for name in service.REQUIRED_ACCOUNTS}
		self.warehouse = _warehouse()
		self.vehicles = {}

	def exists(self, doctype, filters):
		if doctype == "Sales Invoice":
			return filters in self.sales_invoices
		if doctype == "Customer":
			return filters in self.customers
		if doctype == "Item":
			return filters in self.items
		if doctype == "Serial No":
			return filters in self.serial_nos
		if doctype == "Warehouse":
			return filters == service.WAREHOUSE and self.warehouse is not None
		if doctype == "Account":
			return filters in self.accounts
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		if doctype == "Sales Invoice":
			for invoice in self.sales_invoices.values():
				if (
					getattr(invoice, "company", None) == filters.get("company")
					and getattr(invoice, "docstatus", None) == filters.get("docstatus")
					and service.QA_REMARKS_MARKER in (getattr(invoice, "remarks", "") or "")
				):
					return invoice.name
			return None
		if doctype == "Used Car Vehicle":
			for vehicle in self.vehicles.values():
				if getattr(vehicle, "sales_invoice", None) == filters.get("sales_invoice"):
					return vehicle.name
			return None
		return None

	def get_all(self, doctype, filters=None, fields=None, order_by=None, limit=None):
		if doctype != "Used Car Vehicle":
			return []
		vehicles = [vehicle for vehicle in self.vehicles.values() if getattr(vehicle, "sales_invoice", None)]
		vehicles.sort(key=lambda vehicle: getattr(vehicle, "modified", ""), reverse=True)
		rows = []
		for vehicle in vehicles[:limit]:
			rows.append(
				{
					"name": vehicle.name,
					"sales_invoice": vehicle.sales_invoice,
					"status": getattr(vehicle, "status", None),
					"formal_delivery_status": getattr(vehicle, "formal_delivery_status", None),
				}
			)
		return rows

	def count(self, doctype, filters=None):
		key = (doctype, tuple(sorted((filters or {}).items())))
		return self.counts.get(key, 0)

	def set_value(self, *args, **kwargs):
		raise AssertionError("set_value must not be called")

	def commit(self):
		raise AssertionError("commit must not be called")

	def rollback(self):
		raise AssertionError("rollback must not be called")


class FakeFrappe:
	def __init__(self, fake_db):
		self.db = fake_db
		self.local = SimpleNamespace(site=service.EXPECTED_CLEAN_SITE)

	def get_doc(self, doctype, name=None):
		if doctype == "Sales Invoice":
			return self.db.sales_invoices[name]
		if doctype == "Item":
			return self.db.items[name]
		if doctype == "Serial No":
			return self.db.serial_nos[name]
		if doctype == "Warehouse":
			return self.db.warehouse
		if doctype == "Account":
			return self.db.accounts[name]
		if doctype == "Used Car Vehicle":
			return self.db.vehicles[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

	def get_value(self, *args, **kwargs):
		raise AssertionError("frappe.get_value must not be called")


class UnsafeDoc(SimpleNamespace):
	def submit(self):
		raise AssertionError("submit must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def insert(self):
		raise AssertionError("insert must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")


def _account(name, is_group=0, disabled=0):
	return UnsafeDoc(name=name, company=service.COMPANY, is_group=is_group, disabled=disabled)


def _warehouse():
	return UnsafeDoc(
		name=service.WAREHOUSE,
		company=service.COMPANY,
		is_group=0,
		disabled=0,
		account=service.INVENTORY_ACCOUNT,
	)


def _item(name, has_serial_no=1):
	return UnsafeDoc(name=name, item_code=name, has_serial_no=has_serial_no)


def _invoice(**overrides):
	data = {
		"name": "ACC-SINV-2026-00002",
		"company": service.COMPANY,
		"docstatus": 0,
		"update_stock": 1,
		"customer": "CUST-P1-ACC-6E",
		"taxes_and_charges": service.TAX_TEMPLATE,
		"remarks": service.QA_REMARKS_MARKER,
		"items": [
			UnsafeDoc(
				item_code=service.ITEM_CODE,
				qty=1,
				rate=1000000,
				serial_no="VIN-P1-ACC-6F-A",
				warehouse=service.WAREHOUSE,
				income_account=service.INCOME_ACCOUNT,
				expense_account=service.EXPENSE_ACCOUNT,
			)
		],
		"taxes": [
			UnsafeDoc(
				charge_type="On Net Total",
				account_head=service.TAX_ACCOUNT,
				rate=5,
				included_in_print_rate=1,
			)
		],
	}
	data.update(overrides)
	return UnsafeDoc(**data)


def _formal_invoice(name="ACC-SINV-FORMAL-00001", **overrides):
	data = {
		"name": name,
		"remarks": "中古車正式銷售草稿",
		"customer": "CUST-P1-ACC-6E",
		"items": [
			UnsafeDoc(
				item_code=service.ITEM_CODE,
				qty=1,
				rate=1000000,
				serial_no="VIN-FORMAL-001",
				warehouse=service.WAREHOUSE,
				income_account=service.INCOME_ACCOUNT,
				expense_account=service.EXPENSE_ACCOUNT,
			)
		],
	}
	data.update(overrides)
	return _invoice(**data)


def _vehicle(name="UCV-FORMAL-001", sales_invoice="ACC-SINV-FORMAL-00001", **overrides):
	data = {
		"name": name,
		"sales_invoice": sales_invoice,
		"status": "已售出",
		"formal_delivery_status": "銷售發票草稿",
		"item": service.ITEM_CODE,
		"serial_no": "VIN-FORMAL-001",
		"stock_warehouse": service.WAREHOUSE,
		"modified": "2026-06-19 12:00:00",
	}
	data.update(overrides)
	return UnsafeDoc(**data)


def _fake_environment(monkeypatch):
	fake_db = FakeDB()
	invoice = _invoice()
	fake_db.sales_invoices[invoice.name] = invoice
	fake_db.serial_nos["VIN-P1-ACC-6F-A"] = UnsafeDoc(
		name="VIN-P1-ACC-6F-A",
		item_code=service.ITEM_CODE,
		status="Active",
		warehouse=service.WAREHOUSE,
	)
	fake_frappe = FakeFrappe(fake_db)
	monkeypatch.setattr(service, "frappe", fake_frappe)
	return fake_db, fake_frappe


def test_missing_sales_invoice_fails(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.sales_invoices = {}

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="MISSING-SINV")

	assert report["status"] == "fail"
	assert report["ready_to_submit"] is False
	assert any("Sales Invoice 不存在" in error for error in report["blocking_errors"])


def test_sales_invoice_not_draft_fails(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.sales_invoices["ACC-SINV-2026-00002"].docstatus = 1

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert report["status"] == "fail"
	assert any("docstatus 必須為 0" in error for error in report["blocking_errors"])


def test_update_stock_not_one_fails(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.sales_invoices["ACC-SINV-2026-00002"].update_stock = 0

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert report["status"] == "fail"
	assert any("update_stock 必須為 1" in error for error in report["blocking_errors"])


def test_tax_row_rate_not_five_fails(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.sales_invoices["ACC-SINV-2026-00002"].taxes[0].rate = 4

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert report["status"] == "fail"
	assert any("rate 必須是 5" in error for error in report["blocking_errors"])


def test_tax_row_included_in_print_rate_not_one_fails(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.sales_invoices["ACC-SINV-2026-00002"].taxes[0].included_in_print_rate = 0

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert report["status"] == "fail"
	assert any("included_in_print_rate 必須是 1" in error for error in report["blocking_errors"])


def test_serial_item_missing_serial_no_fails(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.sales_invoices["ACC-SINV-2026-00002"].items[0].serial_no = None

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert report["status"] == "fail"
	assert report["ready_to_submit"] is False
	assert "serial item submit 前必須指定 serial_no。" in report["blocking_errors"]


def test_serial_item_with_matching_serial_no_passes_serial_check(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert not any("Serial No" in error for error in report["blocking_errors"])
	assert "Serial No item_code submit preflight 通過。" in report["validations"]


def test_required_account_disabled_or_group_fails(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.accounts[service.INCOME_ACCOUNT] = _account(service.INCOME_ACCOUNT, disabled=1)
	fake_db.accounts[service.EXPENSE_ACCOUNT] = _account(service.EXPENSE_ACCOUNT, is_group=1)

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert report["status"] == "fail"
	assert any("不可停用" in error for error in report["blocking_errors"])
	assert any("非 group ledger account" in error for error in report["blocking_errors"])


def test_report_schema_is_stable(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice="ACC-SINV-2026-00002")

	assert list(report.keys()) == list(service.REPORT_KEYS)
	assert isinstance(report["validations"], list)
	assert isinstance(report["warnings"], list)
	assert isinstance(report["blocking_errors"], list)


def test_preflight_does_not_call_writing_methods(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	invoice = fake_db.sales_invoices["ACC-SINV-2026-00002"]

	report = service.SubmittedSalesInvoicePreflightService().run(sales_invoice=invoice.name)

	assert report["status"] == "pass"
	assert report["ready_to_submit"] is True


def test_latest_formal_vehicle_preflight_selects_linked_draft(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	formal = _formal_invoice()
	fake_db.sales_invoices[formal.name] = formal
	fake_db.vehicles["UCV-FORMAL-001"] = _vehicle()
	fake_db.serial_nos["VIN-FORMAL-001"] = UnsafeDoc(
		name="VIN-FORMAL-001",
		item_code=service.ITEM_CODE,
		status="Active",
		warehouse=service.WAREHOUSE,
	)

	report = service.run_latest_formal_vehicle_sales_invoice_preflight()

	assert report["sales_invoice"] == formal.name
	assert "Sales Invoice 可由 Used Car Vehicle.sales_invoice 反查正式車輛流程草稿。" in report["validations"]


def test_latest_formal_vehicle_preflight_ignores_qa_draft(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	formal = _formal_invoice()
	fake_db.sales_invoices[formal.name] = formal
	fake_db.vehicles["UCV-QA"] = _vehicle(
		name="UCV-QA",
		sales_invoice="ACC-SINV-2026-00002",
		modified="2026-06-19 13:00:00",
	)
	fake_db.vehicles["UCV-FORMAL-001"] = _vehicle(modified="2026-06-19 12:00:00")
	fake_db.serial_nos["VIN-FORMAL-001"] = UnsafeDoc(
		name="VIN-FORMAL-001",
		item_code=service.ITEM_CODE,
		status="Active",
		warehouse=service.WAREHOUSE,
	)

	report = service.run_latest_formal_vehicle_sales_invoice_preflight()

	assert report["sales_invoice"] == formal.name


def test_latest_formal_vehicle_preflight_not_found_with_only_qa(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.run_latest_formal_vehicle_sales_invoice_preflight()

	assert report["status"] == "fail"
	assert report["ready_to_submit"] is False
	assert "找不到正式車輛流程 Draft Sales Invoice。" in report["blocking_errors"]


def test_latest_formal_vehicle_preflight_skips_non_draft_invoice(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	formal = _formal_invoice(docstatus=1)
	fake_db.sales_invoices[formal.name] = formal
	fake_db.vehicles["UCV-FORMAL-001"] = _vehicle()

	report = service.run_latest_formal_vehicle_sales_invoice_preflight()

	assert report["status"] == "fail"
	assert "找不到正式車輛流程 Draft Sales Invoice。" in report["blocking_errors"]


def test_latest_formal_vehicle_preflight_does_not_call_writing_methods(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	formal = _formal_invoice()
	fake_db.sales_invoices[formal.name] = formal
	fake_db.vehicles["UCV-FORMAL-001"] = _vehicle()
	fake_db.serial_nos["VIN-FORMAL-001"] = UnsafeDoc(
		name="VIN-FORMAL-001",
		item_code=service.ITEM_CODE,
		status="Active",
		warehouse=service.WAREHOUSE,
	)

	report = service.run_latest_formal_vehicle_sales_invoice_preflight()

	assert report["status"] == "pass"
	assert report["ready_to_submit"] is True


def test_default_qa_preflight_behavior_is_preserved(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.run_submitted_sales_invoice_preflight()

	assert report["sales_invoice"] == "ACC-SINV-2026-00002"
	assert "Sales Invoice remarks 包含 P1-ACC-6E QA 標記。" in report["validations"]
