from types import SimpleNamespace

from used_car_erp.used_car_erp.services import vehicle_stock_service as service


class FakeMeta:
	def __init__(self, fields):
		self.fields = set(fields)

	def has_field(self, fieldname):
		return fieldname in self.fields


class FakeDB:
	def __init__(self):
		self.accounts = {}
		self.companies = {"OO": SimpleNamespace(name="OO", stock_adjustment_account="0300001 - Stock Adjustment - O")}
		self.warehouses = {"中古車庫存倉 - O": SimpleNamespace(name="中古車庫存倉 - O", company="OO", is_group=0)}
		self.set_value_called = False

	def exists(self, doctype, filters):
		if doctype == "Account":
			return filters in self.accounts
		if doctype == "Company":
			return filters in self.companies
		if doctype == "Warehouse":
			if isinstance(filters, str):
				return filters in self.warehouses
			return any(warehouse.name == filters.get("name") for warehouse in self.warehouses.values())
		return False

	def get_value(self, doctype, filters, fieldname, order_by=None):
		if doctype == "Company" and isinstance(filters, str):
			return getattr(self.companies[filters], fieldname, None)
		if doctype == "Warehouse" and isinstance(filters, str):
			return getattr(self.warehouses[filters], fieldname, None)
		return None

	def set_value(self, *args, **kwargs):
		self.set_value_called = True
		raise AssertionError("COA or document writes must not be called while building Stock Entry")


class FakeFrappe:
	def __init__(self, db, detail_has_expense_account=True, company_has_stock_adjustment_account=True):
		self.db = db
		self.detail_has_expense_account = detail_has_expense_account
		self.company_has_stock_adjustment_account = company_has_stock_adjustment_account
		self.inserted_doc = None

	def get_meta(self, doctype):
		if doctype == "Stock Entry Detail":
			return FakeMeta({"expense_account"} if self.detail_has_expense_account else set())
		if doctype == "Stock Entry":
			return FakeMeta({"stock_entry_type"})
		if doctype == "Company":
			return FakeMeta({"stock_adjustment_account"} if self.company_has_stock_adjustment_account else set())
		return FakeMeta(set())

	def get_doc(self, doctype_or_doc, name=None):
		if isinstance(doctype_or_doc, dict):
			self.inserted_doc = FakeStockEntryDoc(doctype_or_doc)
			return self.inserted_doc
		if doctype_or_doc == "Account":
			return self.db.accounts[name]
		raise AssertionError(f"Unexpected get_doc: {doctype_or_doc} {name}")

	def throw(self, message):
		raise Exception(message)


class FakeStockEntryDoc:
	def __init__(self, data):
		self.data = data
		self.name = "STE-FAKE"
		self.docstatus = 0
		self.ignore_mandatory = False

	def insert(self, **kwargs):
		if kwargs.get("ignore_mandatory"):
			raise AssertionError("ignore_mandatory must not be used")
		return self

	def submit(self):
		self.docstatus = 1
		return self


class FakeVehicle(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)


class TestVehicleStockService(service.VehicleStockService):
	def _validate_vehicle(self, vehicle):
		return None

	def _ensure_item_can_receive_serial_stock(self, item):
		return None

	def _validate_existing_serial_no(self, vehicle, item):
		return None

	def _validate_submitted_stock_entry(self, stock_entry, vehicle):
		return None

	def _get_submitted_serial_no(self, vehicle):
		return vehicle.vin

	def _update_vehicle_stock_links(self, vehicle, stock_entry_name, serial_no):
		vehicle.stock_entry = stock_entry_name
		vehicle.serial_no = serial_no
		vehicle.status = "庫存中"


def _account(name, company="OO", is_group=0, disabled=0, root_type="Expense"):
	return SimpleNamespace(name=name, company=company, is_group=is_group, disabled=disabled, root_type=root_type)


def _vehicle(**overrides):
	data = {
		"name": "UCV-001",
		"item": "ITEM-001",
		"vin": "VIN-001",
		"stock_warehouse": "中古車庫存倉 - O",
		"purchase_price": 300000,
		"stock_entry": None,
		"serial_no": None,
		"status": "草稿",
	}
	data.update(overrides)
	return FakeVehicle(**data)


def _fake_environment(monkeypatch, detail_has_expense_account=True, company_has_stock_adjustment_account=True):
	db = FakeDB()
	db.accounts["0300001 - Stock Adjustment - O"] = _account("0300001 - Stock Adjustment - O")
	db.accounts[service.FALLBACK_STOCK_ENTRY_DIFFERENCE_ACCOUNT] = _account(service.FALLBACK_STOCK_ENTRY_DIFFERENCE_ACCOUNT)
	fake_frappe = FakeFrappe(
		db,
		detail_has_expense_account=detail_has_expense_account,
		company_has_stock_adjustment_account=company_has_stock_adjustment_account,
	)
	monkeypatch.setattr(service, "frappe", fake_frappe)
	monkeypatch.setattr(service, "nowdate", lambda: "2026-06-19")
	return db, fake_frappe


def test_uses_company_stock_adjustment_account_when_valid(monkeypatch):
	_, fake_frappe = _fake_environment(monkeypatch)

	doc = service.VehicleStockService()._build_stock_entry_doc(_vehicle())

	assert doc["items"][0]["expense_account"] == "0300001 - Stock Adjustment - O"
	assert doc["stock_entry_type"] == "Material Receipt"


def test_uses_fallback_when_company_stock_adjustment_account_empty(monkeypatch):
	db, _ = _fake_environment(monkeypatch)
	db.companies["OO"].stock_adjustment_account = None

	doc = service.VehicleStockService()._build_stock_entry_doc(_vehicle())

	assert doc["items"][0]["expense_account"] == service.FALLBACK_STOCK_ENTRY_DIFFERENCE_ACCOUNT


def test_difference_account_missing_blocks_stock_in(monkeypatch):
	db, _ = _fake_environment(monkeypatch)
	db.companies["OO"].stock_adjustment_account = None
	del db.accounts[service.FALLBACK_STOCK_ENTRY_DIFFERENCE_ACCOUNT]

	try:
		service.VehicleStockService()._build_stock_entry_doc(_vehicle())
	except Exception as exc:
		assert "找不到可用的 Stock Entry Difference Account" in str(exc)
	else:
		raise AssertionError("missing difference account must block")


def test_group_difference_account_blocks_stock_in(monkeypatch):
	db, _ = _fake_environment(monkeypatch)
	db.accounts["0300001 - Stock Adjustment - O"] = _account("0300001 - Stock Adjustment - O", is_group=1)

	try:
		service.VehicleStockService()._build_stock_entry_doc(_vehicle())
	except Exception as exc:
		assert "必須是非群組會計科目" in str(exc)
	else:
		raise AssertionError("group difference account must block")


def test_disabled_difference_account_blocks_stock_in(monkeypatch):
	db, _ = _fake_environment(monkeypatch)
	db.accounts["0300001 - Stock Adjustment - O"] = _account("0300001 - Stock Adjustment - O", disabled=1)

	try:
		service.VehicleStockService()._build_stock_entry_doc(_vehicle())
	except Exception as exc:
		assert "不可停用" in str(exc)
	else:
		raise AssertionError("disabled difference account must block")


def test_company_mismatch_difference_account_blocks_stock_in(monkeypatch):
	db, _ = _fake_environment(monkeypatch)
	db.accounts["0300001 - Stock Adjustment - O"] = _account("0300001 - Stock Adjustment - O", company="XX")

	try:
		service.VehicleStockService()._build_stock_entry_doc(_vehicle())
	except Exception as exc:
		assert "必須屬於公司 OO" in str(exc)
	else:
		raise AssertionError("company mismatch difference account must block")


def test_non_expense_difference_account_blocks_stock_in(monkeypatch):
	db, _ = _fake_environment(monkeypatch)
	db.accounts["0300001 - Stock Adjustment - O"] = _account("0300001 - Stock Adjustment - O", root_type="Asset")

	try:
		service.VehicleStockService()._build_stock_entry_doc(_vehicle())
	except Exception as exc:
		assert "root_type 必須是 Expense" in str(exc)
	else:
		raise AssertionError("non-expense difference account must block")


def test_no_expense_account_field_does_not_write_field(monkeypatch):
	_fake_environment(monkeypatch, detail_has_expense_account=False)

	doc = service.VehicleStockService()._build_stock_entry_doc(_vehicle())

	assert "expense_account" not in doc["items"][0]
	assert doc["items"][0]["item_code"] == "ITEM-001"


def test_stock_in_does_not_use_ignore_mandatory(monkeypatch):
	_, fake_frappe = _fake_environment(monkeypatch)
	vehicle = _vehicle()
	original_get_doc = service.frappe.get_doc

	def get_doc(doctype, name=None):
		if doctype == "Used Car Vehicle":
			return vehicle
		if doctype == "Item":
			return SimpleNamespace(name=name)
		return original_get_doc(doctype, name)

	monkeypatch.setattr(service.frappe, "get_doc", get_doc)

	result = TestVehicleStockService().stock_in_vehicle(vehicle.name)

	assert result["created"] is True
	assert fake_frappe.db.set_value_called is False


def test_build_stock_entry_does_not_modify_coa(monkeypatch):
	db, _ = _fake_environment(monkeypatch)

	service.VehicleStockService()._build_stock_entry_doc(_vehicle())

	assert db.set_value_called is False
