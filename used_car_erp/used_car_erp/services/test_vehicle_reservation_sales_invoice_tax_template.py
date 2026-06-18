from types import SimpleNamespace

import pytest

from used_car_erp.used_car_erp.services import vehicle_reservation_service as service


class FakeDB:
	def __init__(self):
		self.tax_templates = {service.SALES_TAX_TEMPLATE: _tax_template()}
		self.accounts = {service.SALES_TAX_ACCOUNT: _account(service.SALES_TAX_ACCOUNT)}
		self.counts = {
			"GL Entry": 0,
			"Stock Ledger Entry": 0,
			"Payment Entry": 0,
			"Journal Entry": 0,
			"Delivery Note": 0,
			"Stock Entry": 0,
		}

	def exists(self, doctype, name):
		if doctype == "Sales Taxes and Charges Template":
			return name in self.tax_templates
		if doctype == "Account":
			return name in self.accounts
		return False

	def count(self, doctype, filters=None):
		return self.counts.get(doctype, 0)

	def commit(self):
		raise AssertionError("commit must not be called")

	def rollback(self):
		raise AssertionError("rollback must not be called")

	def set_value(self, *args, **kwargs):
		raise AssertionError("set_value must not be called")


class FakeFrappe:
	def __init__(self, fake_db):
		self.db = fake_db
		self.inserted_docs = []
		self.submitted_docs = []

	def get_doc(self, doctype_or_doc, name=None):
		if isinstance(doctype_or_doc, dict):
			return FakeInsertableDoc(self, doctype_or_doc)
		if doctype_or_doc == "Sales Taxes and Charges Template":
			return self.db.tax_templates[name]
		if doctype_or_doc == "Account":
			return self.db.accounts[name]
		raise AssertionError(f"Unexpected get_doc: {doctype_or_doc} {name}")

	def throw(self, message):
		raise Exception(message)


class FakeInsertableDoc(SimpleNamespace):
	def insert(self, *args, **kwargs):
		self._fake_frappe.inserted_docs.append(self)
		return self

	def submit(self):
		self._fake_frappe.submitted_docs.append(self)
		raise AssertionError("submit must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")


def _account(name, company="OO", is_group=0, disabled=0):
	return SimpleNamespace(name=name, company=company, is_group=is_group, disabled=disabled)


def _tax_template(
	company="OO",
	disabled=0,
	taxes=None,
	charge_type="On Net Total",
	account_head=None,
	rate=5,
	included_in_print_rate=1,
):
	if taxes is None:
		taxes = [
			SimpleNamespace(
				charge_type=charge_type,
				account_head=account_head or service.SALES_TAX_ACCOUNT,
				rate=rate,
				included_in_print_rate=included_in_print_rate,
				description="營業稅 5%（含稅）",
			)
		]
	return SimpleNamespace(name=service.SALES_TAX_TEMPLATE, company=company, disabled=disabled, taxes=taxes)


def _fake_environment(monkeypatch):
	fake_db = FakeDB()
	fake_frappe = FakeFrappe(fake_db)
	monkeypatch.setattr(service, "frappe", fake_frappe)
	return fake_db, fake_frappe


def _build_valid_payload(fake_frappe):
	tax_row = service.VehicleReservationService()._build_sales_tax_row_from_template("OO")
	return fake_frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": "OO",
			"customer": "CUST-USED-CAR",
			"posting_date": "2026-06-19",
			"due_date": "2026-06-19",
			"update_stock": 1,
			"taxes_and_charges": service.SALES_TAX_TEMPLATE,
			"items": [
				{
					"item_code": "USED-CAR-VEHICLE",
					"qty": 1,
					"rate": 1000000,
					"serial_no": "VIN-USED-CAR",
					"warehouse": "中古車庫存倉 - O",
					"income_account": "0100001-UC - 中古車銷售收入 - O",
				}
			],
			"taxes": [tax_row],
		}
	)


def test_valid_template_adds_tax_template_and_single_tax_row_to_draft_payload(monkeypatch):
	_, fake_frappe = _fake_environment(monkeypatch)

	invoice = _build_valid_payload(fake_frappe)

	assert invoice.taxes_and_charges == service.SALES_TAX_TEMPLATE
	assert len(invoice.taxes) == 1
	assert invoice.taxes[0]["charge_type"] == "On Net Total"
	assert invoice.taxes[0]["account_head"] == service.SALES_TAX_ACCOUNT
	assert invoice.taxes[0]["rate"] == service.SALES_TAX_RATE
	assert invoice.taxes[0]["included_in_print_rate"] == 1


def test_missing_template_blocks(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.tax_templates = {}

	with pytest.raises(Exception, match="找不到 Sales Taxes and Charges Template"):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


def test_template_company_mismatch_blocks(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.SALES_TAX_TEMPLATE] = _tax_template(company="OTHER")

	with pytest.raises(Exception, match="不屬於公司 OO"):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


def test_template_disabled_blocks(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.SALES_TAX_TEMPLATE] = _tax_template(disabled=1)

	with pytest.raises(Exception, match="已停用"):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


def test_template_tax_row_count_not_one_blocks(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.SALES_TAX_TEMPLATE] = _tax_template(taxes=[])

	with pytest.raises(Exception, match="有且只有一筆稅項"):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


def test_tax_row_account_head_mismatch_blocks(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.SALES_TAX_TEMPLATE] = _tax_template(account_head="WRONG - O")

	with pytest.raises(Exception, match="account_head 必須是"):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


def test_tax_row_rate_not_five_blocks(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.SALES_TAX_TEMPLATE] = _tax_template(rate=4)

	with pytest.raises(Exception, match="rate 必須是 5"):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


def test_tax_row_included_in_print_rate_not_one_blocks(monkeypatch):
	fake_db, _ = _fake_environment(monkeypatch)
	fake_db.tax_templates[service.SALES_TAX_TEMPLATE] = _tax_template(included_in_print_rate=0)

	with pytest.raises(Exception, match="included_in_print_rate 必須是 1"):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


@pytest.mark.parametrize(
	"account, message",
	[
		(None, "不存在"),
		(_account(service.SALES_TAX_ACCOUNT, company="OTHER"), "不屬於公司 OO"),
		(_account(service.SALES_TAX_ACCOUNT, is_group=1), "是群組科目"),
		(_account(service.SALES_TAX_ACCOUNT, disabled=1), "已停用"),
	],
)
def test_tax_account_invalid_blocks(monkeypatch, account, message):
	fake_db, _ = _fake_environment(monkeypatch)
	if account is None:
		fake_db.accounts = {}
	else:
		fake_db.accounts[service.SALES_TAX_ACCOUNT] = account

	with pytest.raises(Exception, match=message):
		service.VehicleReservationService()._build_sales_tax_row_from_template("OO")


def test_tax_helper_does_not_submit_create_ledgers_or_modify_coa(monkeypatch):
	fake_db, fake_frappe = _fake_environment(monkeypatch)
	before_counts = {doctype: fake_db.count(doctype) for doctype in fake_db.counts}

	service.VehicleReservationService()._build_sales_tax_row_from_template("OO")

	assert {doctype: fake_db.count(doctype) for doctype in fake_db.counts} == before_counts
	assert fake_frappe.inserted_docs == []
	assert fake_frappe.submitted_docs == []
