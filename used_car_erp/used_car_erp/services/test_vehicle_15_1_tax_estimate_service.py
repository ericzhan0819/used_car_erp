from types import SimpleNamespace

from used_car_erp.used_car_erp.services import vehicle_15_1_tax_estimate_service as service


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
	def __init__(self, db, fields=None):
		self.db = db
		self.fields = fields or {
			"name",
			"status",
			"purchase_price",
			"sold_price",
			"sales_invoice",
			"vehicle_tax_mode",
			"purchase_source_type",
			"purchase_document_type",
			"tax_review_status",
			"tax_review_note",
		}

	def get_doc(self, doctype, name=None):
		return self.db.docs[doctype][name]

	def get_meta(self, doctype):
		return FakeMeta(self.fields if doctype == "Used Car Vehicle" else set())

	def whitelist(self):
		return lambda fn: fn

	def delete_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("delete_doc")
		raise AssertionError("delete_doc must not be called")


def _fake_environment(monkeypatch, fields=None):
	db = FakeDB()
	fake = FakeFrappe(db, fields=fields)
	monkeypatch.setattr(service, "frappe", fake)
	return db


def _base_docs():
	return {
		"Used Car Vehicle": {"UCV-TAX": _vehicle()},
		"Sales Invoice": {"SINV-TAX": _invoice()},
		"Used Car Vehicle Cost": {"COST-TAX": FakeDoc(name="COST-TAX", vehicle="UCV-TAX", amount=999999, cost_category="維修")},
	}


def _vehicle(**overrides):
	data = {
		"name": "UCV-TAX",
		"status": "已售出",
		"purchase_price": 315000,
		"sold_price": 378000,
		"sales_invoice": "SINV-TAX",
		"vehicle_tax_mode": "15-1 特殊扣抵",
		"purchase_source_type": "個人",
		"purchase_document_type": "買賣合約",
		"tax_review_status": "已初步判斷",
		"tax_review_note": "測試備註",
		"modified": "2026-06-19 23:00:00",
	}
	data.update(overrides)
	return FakeDoc(**data)


def _invoice(**overrides):
	data = {"name": "SINV-TAX", "docstatus": 1, "grand_total": 378000, "remarks": "formal", "title": "formal"}
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
	return service.Vehicle151TaxEstimateService().run(vehicle_name="UCV-TAX", **kwargs)


def test_target_not_found_fails_not_ready(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"] = {}
	report = service.Vehicle151TaxEstimateService().run()
	assert report["status"] == "fail"
	assert report["ready_for_vehicle_page"] is False


def test_vehicle_missing_purchase_price_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].purchase_price = None
	report = _run()
	assert report["status"] == "fail"
	assert report["purchase_price_source"] == "used_car_vehicle_purchase_price"


def test_vehicle_missing_sale_price_fails(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].sold_price = None
	db.docs["Used Car Vehicle"]["UCV-TAX"].sales_invoice = None
	report = _run()
	assert report["status"] == "fail"


def test_purchase_price_must_be_positive(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].purchase_price = 0
	report = _run()
	assert report["status"] == "fail"


def test_sale_price_must_be_positive(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].sold_price = 0
	db.docs["Used Car Vehicle"]["UCV-TAX"].sales_invoice = None
	report = _run()
	assert report["status"] == "fail"


def test_15_1_tax_mode_pass(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["status"] == "pass"
	assert report["estimate_reliable"] is True


def test_pending_tax_mode_is_warning_not_reliable(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].vehicle_tax_mode = "待確認"
	report = _run()
	assert report["status"] == "warning"
	assert report["estimate_reliable"] is False


def test_blank_tax_mode_is_warning_not_reliable(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].vehicle_tax_mode = ""
	report = _run()
	assert report["status"] == "warning"
	assert report["estimate_reliable"] is False


def test_non_deductible_tax_mode_sets_deduction_to_zero(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].vehicle_tax_mode = "不可扣抵"
	report = _run()
	assert report["allowed_deduction_raw"] == 0
	assert report["estimated_business_tax_raw"] == report["output_tax_raw"]


def test_general_invoice_tax_mode_is_warning_and_not_formal_15_1(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].vehicle_tax_mode = "一般發票扣抵"
	report = _run()
	assert report["status"] == "warning"
	assert report["tax_mode_applicability"] == "一般發票扣抵，不使用 15-1 公式"


def test_sale_price_uses_vehicle_sold_price(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].sales_invoice = None
	report = _run()
	assert report["sale_price"] == 378000
	assert report["sale_price_source"] == "used_car_vehicle_sold_price"


def test_sale_price_fallback_uses_sales_invoice_grand_total(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].sold_price = None
	report = _run()
	assert report["sale_price"] == 378000
	assert report["sale_price_source"] == "sales_invoice_grand_total"


def test_sale_price_mismatch_warns_and_uses_sales_invoice(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].sold_price = 370000
	report = _run()
	assert report["status"] == "warning"
	assert report["sale_price"] == 378000
	assert report["sale_price_source"] == "sales_invoice_grand_total"


def test_315000_378000_example(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["output_tax_raw"] == 18000
	assert report["input_tax_estimate_raw"] == 15000
	assert report["allowed_deduction_raw"] == 15000
	assert report["estimated_business_tax_raw"] == 3000


def test_input_tax_capped_at_output_tax(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].purchase_price = 420000
	db.docs["Used Car Vehicle"]["UCV-TAX"].sold_price = 210000
	db.docs["Sales Invoice"]["SINV-TAX"].grand_total = 210000
	report = _run()
	assert report["allowed_deduction_raw"] == report["output_tax_raw"]
	assert report["estimated_business_tax_raw"] == 0


def test_excluded_cost_categories_are_fixed(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert report["excluded_cost_categories"] == ["整備費", "維修費", "美容費", "拍場費", "代辦費", "其他後續支出"]


def test_service_does_not_read_vehicle_cost_for_purchase_price(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Vehicle"]["UCV-TAX"].purchase_price = None
	report = _run()
	assert report["status"] == "fail"
	assert report["purchase_price"] == 0


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
	rows = service.find_vehicle_15_1_tax_estimate_candidates(limit=10)
	assert [row["vehicle"] for row in rows] == ["UCV-NEW", "UCV-TAX"]
	assert db.forbidden_calls == []


def test_summary_cards_include_required_labels(monkeypatch):
	_fake_environment(monkeypatch)
	report = _run()
	assert [card["label"] for card in report["summary_cards"]] == ["售車銷項稅額", "15-1 可扣抵估算", "預估本車營業稅"]
