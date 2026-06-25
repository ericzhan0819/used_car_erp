import frappe


USED_CAR_CASH_ACCOUNTS = [
	{
		"account_name": "現金",
		"account_type": "現金",
		"is_default": 1,
		"opening_balance": 0,
		"is_active": 1,
		"sort_order": 10,
	},
	{
		"account_name": "主要銀行",
		"account_type": "銀行",
		"is_default": 0,
		"opening_balance": 0,
		"is_active": 1,
		"sort_order": 20,
	},
	{
		"account_name": "其他",
		"account_type": "其他",
		"is_default": 0,
		"opening_balance": 0,
		"is_active": 1,
		"sort_order": 90,
	},
]


def execute():
	for row in USED_CAR_CASH_ACCOUNTS:
		upsert_used_car_cash_account(row)


def upsert_used_car_cash_account(row):
	account_name = row["account_name"]
	values = {
		"account_type": row["account_type"],
		"is_default": row.get("is_default", 0),
		"opening_balance": row.get("opening_balance", 0),
		"is_active": row.get("is_active", 1),
		"sort_order": row.get("sort_order"),
	}

	if frappe.db.exists("Used Car Cash Account", account_name):
		doc = frappe.get_doc("Used Car Cash Account", account_name)
		for fieldname, value in values.items():
			doc.set(fieldname, value)
		doc.save()
		return

	doc = frappe.get_doc(
		{
			"doctype": "Used Car Cash Account",
			"account_name": account_name,
			**values,
		}
	)
	doc.insert()
