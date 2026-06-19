from types import SimpleNamespace

from used_car_erp.used_car_erp.services import vehicle_management_profit_summary_service as service


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


class FakeTaxService:
	def __init__(self, status="pass"):
		self.status = status

	def run(self, vehicle_name=None, sales_invoice=None):
		return {
			"status": self.status,
			"sale_price": 378000,
			"purchase_price": 315000,
			"allowed_deduction_raw": 15000,
			"estimated_business_tax_raw": 3000,
			"excluded_cost_categories": ["整備費", "維修費", "美容費", "拍場費", "代辦費", "其他後續支出"],
		}


def _fake_environment(monkeypatch, tax_status="pass"):
	db = FakeDB()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	monkeypatch.setattr(service, "Vehicle151TaxEstimateService", lambda: FakeTaxService(tax_status))
	return db


def _base_docs():
	return {
		"Used Car Vehicle": {"UCV-MGMT": _vehicle()},
		"Sales Invoice": {"SINV-MGMT": _invoice()},
		"Used Car Vehicle Cost": {
			"COST-1": _cost(name="COST-1", cost_category="整備", amount=10000),
			"COST-2": _cost(name="COST-2", cost_category="維修", amount=5000),
			"COST-3": _cost(name="COST-3", cost_category="美容", amount=3000),
			"COST-4": _cost(name="COST-4", cost_category="拍場費", amount=2000),
			"COST-5": _cost(name="COST-5", cost_category="過戶相關", amount=1000),
		},
		"Used Car Money Flow": {
			"MF-DEPOSIT": _money_flow(name="MF-DEPOSIT", flow_type="訂金收款", amount=50000),
			"MF-FINAL": _money_flow(name="MF-FINAL", flow_type="尾款收款", amount=328000),
			"MF-INCOME": _money_flow(name="MF-INCOME", flow_type="其他收入", amount=2000),
		},
	}


def _vehicle(**overrides):
	data = {"name": "UCV-MGMT", "status": "已售出", "purchase_price": 315000, "sold_price": 378000, "sales_invoice": "SINV-MGMT", "modified": "2026-06-19 23:00:00"}
	data.update(overrides)
	return FakeDoc(**data)


def _invoice(**overrides):
	data = {"name": "SINV-MGMT", "docstatus": 1, "grand_total": 378000, "remarks": "formal", "title": "formal", "items": []}
	data.update(overrides)
	return FakeDoc(**data)


def _cost(**overrides):
	data = {"name": "COST", "vehicle": "UCV-MGMT", "cost_category": "整備", "amount": 1000, "capitalization_mode": "單車成本", "cost_date": "2026-06-19", "modified": "2026-06-19 23:00:00"}
	data.update(overrides)
	return FakeDoc(**data)


def _money_flow(**overrides):
	data = {"name": "MF", "vehicle": "UCV-MGMT", "flow_type": "其他收入", "direction": "收入", "amount": 1000, "status": "已入帳", "payment_date": "2026-06-19", "modified": "2026-06-19 23:00:00"}
	data.update(overrides)
	return FakeDoc(**data)


def _matches(doc, filters):
	for key, expected in filters.items():
		actual = doc.get(key)
		if isinstance(expected, list):
			operator = expected[0]
			value = expected[1] if len(expected) > 1 else None
			if operator == "in" and actual not in value:
				return False
			if operator == ">" and not (actual is not None and actual > value):
				return False
			continue
		if actual != expected:
			return False
	return True


def _project(doc, fields):
	return {field: doc.get(field) for field in fields or ()}


def _run():
	return service.VehicleManagementProfitSummaryService().run(vehicle_name="UCV-MGMT")


def test_target_not_found_fails_not_ready(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"] = {}
	report = service.VehicleManagementProfitSummaryService().run()
	assert report["status"] == "fail"
	assert report["ready_for_vehicle_page"] is False


def test_sold_vehicle_missing_purchase_price_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].purchase_price = None
	report = _run()
	assert report["status"] == "fail"


def test_unsold_vehicle_missing_sale_price_warns_ready(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].status = "庫存中"
	db.docs["Used Car Vehicle"]["UCV-MGMT"].sold_price = None
	db.docs["Used Car Vehicle"]["UCV-MGMT"].sales_invoice = None
	report = _run()
	assert report["status"] == "warning"
	assert report["ready_for_vehicle_page"] is True
	assert report["management_gross_profit"] is None


def test_sale_price_uses_vehicle_sold_price(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].sales_invoice = None
	report = _run()
	assert report["sale_price"] == 378000
	assert report["sale_price_source"] == "used_car_vehicle_sold_price"


def test_sale_price_fallback_uses_sales_invoice_grand_total(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].sold_price = None
	report = _run()
	assert report["sale_price"] == 378000
	assert report["sale_price_source"] == "sales_invoice_grand_total"


def test_sale_price_mismatch_warns_submitted_si_uses_grand_total(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].sold_price = 370000
	report = _run()
	assert report["status"] == "warning"
	assert report["sale_price"] == 378000
	assert report["sale_price_source"] == "sales_invoice_grand_total"


def test_purchase_price_not_inferred_from_vehicle_cost(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].purchase_price = None
	db.docs["Used Car Vehicle Cost"] = {"PURCHASE-COST": _cost(name="PURCHASE-COST", cost_category="購車價", amount=315000)}
	report = _run()
	assert report["status"] == "fail"
	assert report["purchase_price"] == 0


def test_vehicle_cost_rows_sum_to_direct_cost_total(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["direct_cost_total"] == 21000


def test_purchase_price_cost_category_excluded_and_warns(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle Cost"]["COST-PURCHASE"] = _cost(name="COST-PURCHASE", cost_category="購車價", amount=315000)
	report = _run()
	assert report["direct_cost_total"] == 21000
	assert report["status"] == "warning"


def test_direct_cost_categories_enter_management_profit(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["cost_breakdown"] == {"整備費": 10000, "維修費": 5000, "美容費": 3000, "拍場費": 2000, "代辦費": 1000}


def test_direct_cost_categories_excluded_from_15_1_tax_base(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["excluded_from_15_1_tax_base"] == ["整備費", "維修費", "美容費", "拍場費", "代辦費", "其他後續支出"]
	assert report["tax_estimate_summary"]["excluded_cost_categories"] == report["excluded_from_15_1_tax_base"]


def test_deposit_and_final_payment_not_double_counted(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["other_direct_income"] == 2000
	assert [row["name"] for row in report["other_direct_income_rows"]] == ["MF-INCOME"]


def test_other_direct_income_adds_back(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["other_direct_income"] == 2000


def test_management_gross_profit_formula(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["management_gross_profit"] == 44000


def test_management_gross_margin_rate(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["management_gross_margin_rate"] == round(44000 / 378000, 6)


def test_negative_profit_is_not_fail(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].purchase_price = 500000
	report = _run()
	assert report["management_gross_profit"] < 0
	assert report["status"] == "pass"


def test_tax_estimate_warning_does_not_block_management_profit(monkeypatch):
	_fake_environment(monkeypatch, tax_status="warning")
	report = _run()
	assert report["status"] == "pass"
	assert report["tax_estimate_status"] == "warning"
	assert report["management_gross_profit"] == 44000


def test_summary_cards_include_required_labels(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert [card["label"] for card in report["summary_cards"]] == ["成交價", "購車價", "直接成本", "管理毛利", "管理毛利率"]


def test_service_does_not_call_writing_methods(monkeypatch):
	db = _fake_environment(monkeypatch)
	report = _run()
	assert report["status"] == "pass"
	assert db.forbidden_calls == []
	assert list(report.keys()) == list(service.REPORT_KEYS)


def test_candidate_finder_returns_latest_vehicles_and_does_not_write(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-NEW"] = _vehicle(name="UCV-NEW", sales_invoice=None, sold_price=400000, modified="2026-06-19 23:30:00")
	db.docs["Used Car Vehicle"]["UCV-QA"] = _vehicle(name="UCV-QA", sales_invoice="SINV-QA", sold_price=400000, modified="2026-06-19 23:40:00")
	db.docs["Sales Invoice"]["SINV-QA"] = _invoice(name="SINV-QA", remarks="P1-ACC-6E QA draft")
	rows = service.find_vehicle_management_profit_summary_candidates(limit=10)
	assert [row["vehicle"] for row in rows] == ["UCV-NEW", "UCV-MGMT"]
	assert db.forbidden_calls == []


def test_sales_invoice_target_can_resolve_from_item_when_vehicle_link_missing(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-MGMT"].sales_invoice = None
	db.docs["Used Car Vehicle"]["UCV-MGMT"].item = "ITEM-MGMT"
	db.docs["Sales Invoice"]["SINV-MGMT"].items = [FakeDoc(item_code="ITEM-MGMT")]
	report = service.VehicleManagementProfitSummaryService().run(sales_invoice="SINV-MGMT")
	assert report["vehicle"] == "UCV-MGMT"
	assert report["status"] == "warning"
