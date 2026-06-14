import frappe


TAIWAN_ACCOUNTING_ITEM_CODES = [
	{
		"code": "0100001",
		"item_name": "營業收入總額",
		"category": "Income",
		"statement_type": "Profit and Loss",
		"normal_balance": "Credit",
		"is_group_like": 1,
		"source_year": "113",
	},
	{
		"code": "0100004",
		"item_name": "營業收入淨額",
		"category": "Income",
		"statement_type": "Profit and Loss",
		"normal_balance": "Credit",
		"is_group_like": 1,
		"source_year": "113",
	},
	{
		"code": "0100005",
		"item_name": "營業成本",
		"category": "Cost",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 1,
		"source_year": "113",
	},
	{
		"code": "0201130",
		"item_name": "存貨",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 1,
		"source_year": "113",
	},
	{
		"code": "0201131",
		"item_name": "商品",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0300090",
		"item_name": "營業成本",
		"category": "InventoryCost",
		"statement_type": "Cost Statement",
		"normal_balance": "Debit",
		"is_group_like": 1,
		"source_year": "113",
	},
	{
		"code": "0201111",
		"item_name": "現金",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0201112",
		"item_name": "銀行存款",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0201123",
		"item_name": "應收帳款",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0201129",
		"item_name": "其他應收款",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0201144",
		"item_name": "進項稅款",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0201145",
		"item_name": "留抵稅額",
		"category": "Asset",
		"statement_type": "Balance Sheet",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0202132",
		"item_name": "應付稅捐",
		"category": "Liability",
		"statement_type": "Balance Sheet",
		"normal_balance": "Credit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0202134",
		"item_name": "銷項稅額",
		"category": "Liability",
		"statement_type": "Balance Sheet",
		"normal_balance": "Credit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0202121",
		"item_name": "應付帳款",
		"category": "Liability",
		"statement_type": "Balance Sheet",
		"normal_balance": "Credit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0202130",
		"item_name": "其他應付款",
		"category": "Liability",
		"statement_type": "Balance Sheet",
		"normal_balance": "Credit",
		"is_group_like": 1,
		"source_year": "113",
	},
	{
		"code": "0202136",
		"item_name": "預收款項",
		"category": "Liability",
		"statement_type": "Balance Sheet",
		"normal_balance": "Credit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0202137",
		"item_name": "預收貨款",
		"category": "Liability",
		"statement_type": "Balance Sheet",
		"normal_balance": "Credit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0202138",
		"item_name": "其他預收款",
		"category": "Liability",
		"statement_type": "Balance Sheet",
		"normal_balance": "Credit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0100016",
		"item_name": "修繕費",
		"category": "Expense",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0100017",
		"item_name": "廣告費",
		"category": "Expense",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0100018",
		"item_name": "水電瓦斯費",
		"category": "Expense",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0100019",
		"item_name": "保險費",
		"category": "Expense",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0100022",
		"item_name": "稅捐",
		"category": "Expense",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0100030",
		"item_name": "佣金支出",
		"category": "Expense",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 0,
		"source_year": "113",
	},
	{
		"code": "0100032",
		"item_name": "其他費用",
		"category": "Expense",
		"statement_type": "Profit and Loss",
		"normal_balance": "Debit",
		"is_group_like": 1,
		"source_year": "113",
	},
]


def execute():
	for row in TAIWAN_ACCOUNTING_ITEM_CODES:
		upsert_taiwan_accounting_item_code(row)


def upsert_taiwan_accounting_item_code(row):
	code = row["code"].strip().upper()
	values = {
		"item_name": row["item_name"],
		"category": row["category"],
		"statement_type": row["statement_type"],
		"normal_balance": row.get("normal_balance") or "None",
		"is_group_like": row.get("is_group_like", 0),
		"is_active": row.get("is_active", 1),
		"source_year": row.get("source_year") or "113",
		"source_note": row.get("source_note"),
	}

	if frappe.db.exists("Taiwan Accounting Item Code", code):
		doc = frappe.get_doc("Taiwan Accounting Item Code", code)
		for fieldname, value in values.items():
			doc.set(fieldname, value)
		doc.save()
		return

	doc = frappe.get_doc(
		{
			"doctype": "Taiwan Accounting Item Code",
			"code": code,
			**values,
		}
	)
	doc.insert()
