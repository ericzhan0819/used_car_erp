import frappe
from frappe.utils import cint, flt, getdate


INCLUDED_SETTLEMENT_STATUSES = ("已收款", "已付款", "部分收款", "部分付款")
PENDING_SETTLEMENT_STATUSES = ("待收款", "待付款")
CANCELLED_OR_NO_PAYMENT_REQUIRED_STATUSES = ("不需收付", "已取消")


def get_cash_account_balance_summary(as_of_date=None, include_inactive=False):
	"""Read-only cash account balance summary based on Cash Account and Money Flow."""
	include_inactive = _as_bool(include_inactive)
	accounts = _get_cash_accounts(include_inactive=include_inactive)
	account_summaries = [_new_account_summary(account) for account in accounts]
	account_by_name = {row["cash_account"]: row for row in account_summaries}
	excluded_summary = _new_excluded_summary()
	as_of = getdate(as_of_date) if as_of_date else None

	for money_flow in _get_money_flows():
		cash_account = money_flow.get("cash_account")
		if not cash_account:
			excluded_summary["missing_cash_account"] += 1
			continue
		if money_flow.get("status") == "已作廢":
			excluded_summary["voided"] += 1
			continue

		settlement_status = money_flow.get("settlement_status")
		if settlement_status in PENDING_SETTLEMENT_STATUSES:
			excluded_summary["not_settled"] += 1
			continue
		if settlement_status in CANCELLED_OR_NO_PAYMENT_REQUIRED_STATUSES:
			excluded_summary["cancelled_or_no_payment_required"] += 1
			continue
		if settlement_status not in INCLUDED_SETTLEMENT_STATUSES:
			excluded_summary["not_settled"] += 1
			continue

		if as_of:
			payment_date = money_flow.get("payment_date")
			# MVP：有 as_of_date 時，付款日期空白無法判斷截止日，保守排除。
			if not payment_date:
				excluded_summary["missing_payment_date"] += 1
				continue
			if getdate(payment_date) > as_of:
				excluded_summary["future_dated"] += 1
				continue

		account_summary = account_by_name.get(cash_account)
		if not account_summary:
			continue

		amount = flt(money_flow.get("amount"))
		if money_flow.get("direction") == "收入":
			account_summary["income_total"] = round(flt(account_summary["income_total"]) + amount, 2)
		elif money_flow.get("direction") == "支出":
			account_summary["expense_total"] = round(flt(account_summary["expense_total"]) + amount, 2)

	for account_summary in account_summaries:
		account_summary["balance"] = round(
			flt(account_summary["opening_balance"]) + flt(account_summary["income_total"]) - flt(account_summary["expense_total"]),
			2,
		)

	return {
		"as_of_date": as_of_date,
		"include_inactive": include_inactive,
		"accounts": account_summaries,
		"totals": _build_totals(account_summaries),
		"excluded_summary": excluded_summary,
	}


def _get_cash_accounts(include_inactive=False):
	filters = {}
	if not include_inactive:
		filters["is_active"] = 1
	return frappe.db.get_all(
		"Used Car Cash Account",
		filters=filters,
		fields=("name", "account_name", "account_type", "opening_balance", "opening_balance_date", "is_active", "sort_order"),
		order_by="sort_order asc, account_type asc, account_name asc",
	)


def _get_money_flows():
	return frappe.db.get_all(
		"Used Car Money Flow",
		fields=("cash_account", "direction", "amount", "payment_date", "settlement_status", "status", "flow_type", "vehicle"),
		order_by="payment_date asc, name asc",
	)


def _as_bool(value):
	if isinstance(value, str) and value.strip().lower() in ("false", "no", "off"):
		return False
	return bool(cint(value))


def _new_account_summary(account):
	opening_balance = flt(account.get("opening_balance"))
	return {
		"cash_account": account.get("name"),
		"account_name": account.get("account_name"),
		"account_type": account.get("account_type"),
		"opening_balance": opening_balance,
		"income_total": 0,
		"expense_total": 0,
		"balance": opening_balance,
		"is_active": int(account.get("is_active") or 0),
		"opening_balance_date": account.get("opening_balance_date"),
	}


def _new_excluded_summary():
	return {
		"missing_cash_account": 0,
		"voided": 0,
		"not_settled": 0,
		"cancelled_or_no_payment_required": 0,
		"future_dated": 0,
		"missing_payment_date": 0,
	}


def _build_totals(account_summaries):
	return {
		"opening_balance": round(sum(flt(row.get("opening_balance")) for row in account_summaries), 2),
		"income_total": round(sum(flt(row.get("income_total")) for row in account_summaries), 2),
		"expense_total": round(sum(flt(row.get("expense_total")) for row in account_summaries), 2),
		"balance": round(sum(flt(row.get("balance")) for row in account_summaries), 2),
	}


@frappe.whitelist()
def run_cash_account_balance_summary(as_of_date=None, include_inactive=False):
	return get_cash_account_balance_summary(as_of_date=as_of_date, include_inactive=include_inactive)
