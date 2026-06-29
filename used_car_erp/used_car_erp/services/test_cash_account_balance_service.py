from used_car_erp.used_car_erp.services import cash_account_balance_service as service


class FakeDB:
	def __init__(self):
		self.docs = _base_docs()
		self.forbidden_calls = []

	def get_all(self, doctype, filters=None, fields=None, order_by=None):
		rows = [doc for doc in self.docs.get(doctype, {}).values() if _matches(doc, filters or {})]
		if doctype == "Used Car Cash Account":
			rows.sort(key=lambda doc: (doc.get("sort_order") is None, doc.get("sort_order") or 0, doc.get("account_type") or "", doc.get("account_name") or ""))
		return [_project(doc, fields) for doc in rows]

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

	def get_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("get_doc")
		raise AssertionError("get_doc must not be called")

	def delete_doc(self, *args, **kwargs):
		self.db.forbidden_calls.append("delete_doc")
		raise AssertionError("delete_doc must not be called")

	def whitelist(self):
		return lambda fn: fn


def _fake_environment(monkeypatch):
	db = FakeDB()
	monkeypatch.setattr(service, "frappe", FakeFrappe(db))
	return db


def _base_docs():
	return {
		"Used Car Cash Account": {
			"現金": _cash_account(name="現金", account_name="現金", account_type="現金", opening_balance=1000, sort_order=1),
			"主要銀行": _cash_account(name="主要銀行", account_name="主要銀行", account_type="銀行", opening_balance=5000, sort_order=2),
			"停用帳戶": _cash_account(name="停用帳戶", account_name="停用帳戶", account_type="其他", opening_balance=700, is_active=0, sort_order=None),
		},
		"Used Car Money Flow": {
			"MF-INCOME": _money_flow(name="MF-INCOME", cash_account="現金", direction="收入", amount=300, settlement_status="已收款"),
			"MF-EXPENSE": _money_flow(name="MF-EXPENSE", cash_account="現金", direction="支出", amount=120, settlement_status="已付款"),
			"MF-PARTIAL-INCOME": _money_flow(name="MF-PARTIAL-INCOME", cash_account="現金", direction="收入", amount=80, settlement_status="部分收款"),
			"MF-PARTIAL-EXPENSE": _money_flow(name="MF-PARTIAL-EXPENSE", cash_account="現金", direction="支出", amount=30, settlement_status="部分付款"),
			"MF-PENDING-INCOME": _money_flow(name="MF-PENDING-INCOME", cash_account="現金", direction="收入", amount=1000, settlement_status="待收款"),
			"MF-PENDING-EXPENSE": _money_flow(name="MF-PENDING-EXPENSE", cash_account="現金", direction="支出", amount=1000, settlement_status="待付款"),
			"MF-NO-PAYMENT": _money_flow(name="MF-NO-PAYMENT", cash_account="現金", direction="收入", amount=1000, settlement_status="不需收付"),
			"MF-CANCELLED": _money_flow(name="MF-CANCELLED", cash_account="現金", direction="收入", amount=1000, settlement_status="已取消"),
			"MF-VOIDED": _money_flow(name="MF-VOIDED", cash_account="現金", direction="收入", amount=1000, settlement_status="已收款", status="已作廢"),
			"MF-MISSING-ACCOUNT": _money_flow(name="MF-MISSING-ACCOUNT", cash_account=None, direction="收入", amount=1000, settlement_status="已收款"),
			"MF-BANK": _money_flow(name="MF-BANK", cash_account="主要銀行", direction="收入", amount=2000, settlement_status="已收款"),
			"MF-INACTIVE": _money_flow(name="MF-INACTIVE", cash_account="停用帳戶", direction="收入", amount=300, settlement_status="已收款"),
		}
	}


def _cash_account(**overrides):
	data = {
		"name": "現金",
		"account_name": "現金",
		"account_type": "現金",
		"opening_balance": 0,
		"opening_balance_date": "2026-06-01",
		"is_active": 1,
		"sort_order": None,
	}
	data.update(overrides)
	return data


def _money_flow(**overrides):
	data = {
		"name": "MF",
		"cash_account": "現金",
		"direction": "收入",
		"amount": 100,
		"payment_date": "2026-06-10",
		"settlement_status": "已收款",
		"status": "已入帳",
		"flow_type": "其他",
		"vehicle": "UCV-TEST",
	}
	data.update(overrides)
	return data


def _matches(doc, filters):
	for key, expected in filters.items():
		actual = doc.get(key)
		if actual != expected:
			return False
	return True


def _project(doc, fields):
	return {field: doc.get(field) for field in fields or ()}


def _account(summary, cash_account):
	return next(row for row in summary["accounts"] if row["cash_account"] == cash_account)


def test_opening_balance_and_included_money_flows_calculate_balance(monkeypatch):
	db = _fake_environment(monkeypatch)
	summary = service.get_cash_account_balance_summary()
	cash = _account(summary, "現金")

	assert cash["opening_balance"] == 1000
	assert cash["income_total"] == 380
	assert cash["expense_total"] == 150
	assert cash["balance"] == 1230
	assert summary["totals"] == {"opening_balance": 6000, "income_total": 2380, "expense_total": 150, "balance": 8230}
	assert db.forbidden_calls == []


def test_excluded_money_flow_summary_counts_non_balance_rows(monkeypatch):
	_fake_environment(monkeypatch)
	summary = service.get_cash_account_balance_summary()

	assert summary["excluded_summary"]["missing_cash_account"] == 1
	assert summary["excluded_summary"]["voided"] == 1
	assert summary["excluded_summary"]["not_settled"] == 2
	assert summary["excluded_summary"]["cancelled_or_no_payment_required"] == 2


def test_different_cash_accounts_are_summarized_separately(monkeypatch):
	_fake_environment(monkeypatch)
	summary = service.get_cash_account_balance_summary()

	assert _account(summary, "現金")["balance"] == 1230
	assert _account(summary, "主要銀行")["balance"] == 7000


def test_include_inactive_false_excludes_inactive_accounts(monkeypatch):
	_fake_environment(monkeypatch)
	summary = service.get_cash_account_balance_summary()

	assert [row["cash_account"] for row in summary["accounts"]] == ["現金", "主要銀行"]
	assert summary["include_inactive"] is False


def test_include_inactive_true_includes_inactive_accounts(monkeypatch):
	_fake_environment(monkeypatch)
	summary = service.get_cash_account_balance_summary(include_inactive=True)

	inactive = _account(summary, "停用帳戶")
	assert inactive["is_active"] == 0
	assert inactive["opening_balance"] == 700
	assert inactive["income_total"] == 300
	assert inactive["balance"] == 1000


def test_as_of_date_includes_only_money_flows_on_or_before_date(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Money Flow"] = {
		"MF-BEFORE": _money_flow(name="MF-BEFORE", cash_account="現金", direction="收入", amount=100, payment_date="2026-06-10", settlement_status="已收款"),
		"MF-ON-DATE": _money_flow(name="MF-ON-DATE", cash_account="現金", direction="支出", amount=40, payment_date="2026-06-15", settlement_status="已付款"),
		"MF-FUTURE": _money_flow(name="MF-FUTURE", cash_account="現金", direction="收入", amount=500, payment_date="2026-06-16", settlement_status="已收款"),
		"MF-MISSING-DATE": _money_flow(name="MF-MISSING-DATE", cash_account="現金", direction="收入", amount=700, payment_date=None, settlement_status="已收款"),
	}

	summary = service.get_cash_account_balance_summary(as_of_date="2026-06-15")
	cash = _account(summary, "現金")

	assert summary["as_of_date"] == "2026-06-15"
	assert cash["income_total"] == 100
	assert cash["expense_total"] == 40
	assert cash["balance"] == 1060
	assert summary["excluded_summary"]["future_dated"] == 1
	assert summary["excluded_summary"]["missing_payment_date"] == 1


def test_missing_payment_date_is_included_when_as_of_date_is_empty(monkeypatch):
	db = _fake_environment(monkeypatch)
	db.docs["Used Car Money Flow"] = {
		"MF-MISSING-DATE": _money_flow(name="MF-MISSING-DATE", cash_account="現金", direction="收入", amount=700, payment_date=None, settlement_status="已收款"),
	}

	summary = service.get_cash_account_balance_summary()

	assert _account(summary, "現金")["income_total"] == 700
	assert summary["excluded_summary"]["missing_payment_date"] == 0


def test_service_does_not_call_writing_methods(monkeypatch):
	db = _fake_environment(monkeypatch)
	service.get_cash_account_balance_summary(as_of_date="2026-06-30", include_inactive=True)

	assert db.forbidden_calls == []
