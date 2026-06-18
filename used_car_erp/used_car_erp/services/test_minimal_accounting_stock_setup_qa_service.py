from types import SimpleNamespace

from used_car_erp.used_car_erp.services import minimal_accounting_stock_setup_qa_service as service


class FakeDB:
	def __init__(self):
		self.counts = {
			("GL Entry", (("company", service.COMPANY),)): 0,
			("Stock Ledger Entry", (("company", service.COMPANY),)): 0,
		}
		self.customer_name = None

	def exists(self, doctype, name):
		if doctype == "Company" and name == service.COMPANY:
			return True
		if doctype == "Account":
			return name in self.accounts
		if doctype == "Warehouse" and name == service.WAREHOUSE:
			return True
		if doctype == "Item" and name == service.ITEM_CODE:
			return True
		if doctype == "Sales Taxes and Charges Template":
			return name in self.tax_templates
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		if doctype == "Company" and filters == service.COMPANY and fieldname == "abbr":
			return service.COMPANY_ABBR
		if doctype == "Customer" and filters == {"customer_name": service.QA_CUSTOMER_NAME}:
			return self.customer_name
		if doctype == "Customer Group" and filters == {"is_group": 0}:
			return "Individual"
		if doctype == "Territory" and filters == {"is_group": 0}:
			return "Taiwan"
		return None

	def count(self, doctype, filters=None):
		key = (doctype, tuple(sorted((filters or {}).items())))
		return self.counts.get(key, 0)

	def commit(self):
		raise AssertionError("commit must not be called in fake unit tests")

	def rollback(self):
		raise AssertionError("rollback must not be called in fake unit tests")


class FakeFrappe:
	def __init__(self, fake_db):
		self.db = fake_db
		self.inserted_docs = []
		self.submitted_docs = []
		self.committed = False

	def get_doc(self, doctype_or_doc, name=None):
		if isinstance(doctype_or_doc, dict):
			return FakeInsertableDoc(self, doctype_or_doc)

		doctype = doctype_or_doc
		if doctype == "Company":
			return SimpleNamespace(
				name=service.COMPANY,
				abbr=service.COMPANY_ABBR,
				default_receivable_account=service.RECEIVABLE_ACCOUNT,
				default_income_account=service.INCOME_ACCOUNT,
				default_expense_account=service.EXPENSE_ACCOUNT,
				default_inventory_account=service.INVENTORY_ACCOUNT,
			)
		if doctype == "Account":
			return self.db.accounts[name]
		if doctype == "Warehouse":
			return SimpleNamespace(
				name=service.WAREHOUSE,
				company=service.COMPANY,
				is_group=0,
				disabled=0,
				account=service.INVENTORY_ACCOUNT,
			)
		if doctype == "Item":
			return SimpleNamespace(
				name=service.ITEM_CODE,
				item_group=service.ITEM_GROUP,
				stock_uom=service.STOCK_UOM,
				is_stock_item=1,
				is_sales_item=1,
				is_purchase_item=1,
				has_serial_no=1,
				disabled=0,
				item_defaults=[
					SimpleNamespace(
						company=service.COMPANY,
						default_warehouse=service.WAREHOUSE,
						income_account=service.INCOME_ACCOUNT,
						expense_account=service.EXPENSE_ACCOUNT,
					)
				],
			)
		if doctype == "Sales Taxes and Charges Template":
			return self.db.tax_templates[name]
		raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

	def throw(self, message):
		raise Exception(message)


class FakeInsertableDoc:
	def __init__(self, fake_frappe, data):
		self._fake_frappe = fake_frappe
		self.doctype = data["doctype"]
		self.name = data.get("name")
		for key, value in data.items():
			if key == "items":
				value = [SimpleNamespace(**row) for row in value]
			setattr(self, key, value)
		if self.doctype == "Sales Invoice":
			self.docstatus = 0
			self.taxes = [
				SimpleNamespace(
					account_head=service.TAX_ACCOUNT,
					rate=5,
					included_in_print_rate=1,
				)
			]
			for row in self.items:
				if not hasattr(row, "expense_account"):
					row.expense_account = service.EXPENSE_ACCOUNT

	def insert(self, ignore_permissions=False):
		if self.doctype == "Customer":
			self.name = "CUST-P1-ACC-6E"
			self._fake_frappe.db.customer_name = self.name
		elif self.doctype == "Sales Invoice":
			self.name = "ACC-SINV-P1-ACC-6E"
		self._fake_frappe.inserted_docs.append(self)
		return self

	def submit(self):
		self._fake_frappe.submitted_docs.append(self)
		raise AssertionError("submit must not be called")


def _account(name, is_group=0, disabled=0):
	return SimpleNamespace(name=name, company=service.COMPANY, is_group=is_group, disabled=disabled)


def _tax_template(rate=5, included_in_print_rate=1):
	return SimpleNamespace(
		name=service.INCLUDED_TAX_TEMPLATE,
		company=service.COMPANY,
		disabled=0,
		taxes=[
			SimpleNamespace(
				charge_type="On Net Total",
				account_head=service.TAX_ACCOUNT,
				rate=rate,
				included_in_print_rate=included_in_print_rate,
			)
		],
	)


def _fake_environment(monkeypatch):
	fake_db = FakeDB()
	fake_db.accounts = {name: _account(name) for name in service.REQUIRED_ACCOUNTS}
	fake_db.tax_templates = {
		service.INCLUDED_TAX_TEMPLATE: _tax_template(),
		service.EXCLUDED_TAX_TEMPLATE: _tax_template(included_in_print_rate=0),
	}
	fake_frappe = FakeFrappe(fake_db)
	monkeypatch.setattr(service, "frappe", fake_frappe)
	monkeypatch.setattr(service, "nowdate", lambda: "2026-06-19")
	return fake_db, fake_frappe


def test_normal_master_data_passes_and_creates_draft(monkeypatch):
	_, fake_frappe = _fake_environment(monkeypatch)

	report = service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert report["status"] == "pass"
	assert report["company"] == service.COMPANY
	assert report["customer"] == "CUST-P1-ACC-6E"
	assert report["sales_invoice"] == "ACC-SINV-P1-ACC-6E"
	assert report["gl_entry_count_before"] == 0
	assert report["gl_entry_count_after"] == 0
	assert report["stock_ledger_entry_count_before"] == 0
	assert report["stock_ledger_entry_count_after"] == 0
	assert [doc.doctype for doc in fake_frappe.inserted_docs] == ["Customer", "Sales Invoice"]
	assert fake_frappe.submitted_docs == []


def test_missing_account_fails(monkeypatch):
	fake_db, fake_frappe = _fake_environment(monkeypatch)
	del fake_db.accounts[service.INCOME_ACCOUNT]

	report = service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert report["status"] == "fail"
	assert any("Required Account missing" in error for error in report["errors"])
	assert fake_frappe.inserted_docs == []


def test_group_or_disabled_account_fails(monkeypatch):
	fake_db, fake_frappe = _fake_environment(monkeypatch)
	fake_db.accounts[service.INCOME_ACCOUNT] = _account(service.INCOME_ACCOUNT, is_group=1)
	fake_db.accounts[service.EXPENSE_ACCOUNT] = _account(service.EXPENSE_ACCOUNT, disabled=1)

	report = service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert report["status"] == "fail"
	assert any("must be a ledger account" in error for error in report["errors"])
	assert any("must not be disabled" in error for error in report["errors"])
	assert fake_frappe.inserted_docs == []


def test_tax_template_rate_not_five_fails(monkeypatch):
	fake_db, fake_frappe = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.INCLUDED_TAX_TEMPLATE] = _tax_template(rate=4)

	report = service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert report["status"] == "fail"
	assert any("rate must be 5" in error for error in report["errors"])
	assert fake_frappe.inserted_docs == []


def test_tax_template_included_in_print_rate_fails(monkeypatch):
	fake_db, fake_frappe = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.INCLUDED_TAX_TEMPLATE] = _tax_template(included_in_print_rate=0)

	report = service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert report["status"] == "fail"
	assert any("included_in_print_rate must be 1" in error for error in report["errors"])
	assert fake_frappe.inserted_docs == []


def test_nonzero_gl_or_stock_ledger_count_blocks_draft(monkeypatch):
	fake_db, fake_frappe = _fake_environment(monkeypatch)
	fake_db.counts[("GL Entry", (("company", service.COMPANY),))] = 1
	fake_db.counts[("Stock Ledger Entry", (("company", service.COMPANY),))] = 1

	report = service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert report["status"] == "fail"
	assert "GL Entry count must be 0 before creating QA draft." in report["errors"]
	assert "Stock Ledger Entry count must be 0 before creating QA draft." in report["errors"]
	assert fake_frappe.inserted_docs == []


def test_report_schema_is_stable(monkeypatch):
	_fake_environment(monkeypatch)

	report = service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert list(report.keys()) == list(service.REPORT_KEYS)
	assert isinstance(report["validations"], list)
	assert isinstance(report["warnings"], list)
	assert isinstance(report["errors"], list)


def test_service_does_not_submit_or_commit_in_fake_unit_test(monkeypatch):
	_, fake_frappe = _fake_environment(monkeypatch)

	service.MinimalAccountingStockSetupQAService().run(commit=False)

	assert fake_frappe.submitted_docs == []
	assert fake_frappe.committed is False
