import frappe
from frappe.utils import flt


COMPANY = "OO"
ITEM_CODE = "USED-CAR-VEHICLE"
WAREHOUSE = "中古車庫存倉 - O"
INCOME_ACCOUNT = "0100001-UC - 中古車銷售收入 - O"
EXPENSE_ACCOUNT = "0100005-UC - 中古車銷貨成本 - O"
INVENTORY_ACCOUNT = "0201131 - 商品 - O"
RECEIVABLE_ACCOUNT = "0201123 - 應收帳款 - O"
TAX_ACCOUNT = "0202134 - 銷項稅額 - O"
TAX_TEMPLATE = "台灣營業稅 5%（含稅） - O"
QA_REMARKS_MARKER = "P1-ACC-6E QA Draft Sales Invoice"
EXPECTED_CLEAN_SITE = "erpnext-coa.test"


REQUIRED_ACCOUNTS = (
	INCOME_ACCOUNT,
	EXPENSE_ACCOUNT,
	INVENTORY_ACCOUNT,
	RECEIVABLE_ACCOUNT,
	TAX_ACCOUNT,
)


REPORT_KEYS = (
	"status",
	"ready_to_submit",
	"company",
	"sales_invoice",
	"customer",
	"item_code",
	"serial_no",
	"warehouse",
	"income_account",
	"expense_account",
	"tax_template",
	"tax_account",
	"target_mode",
	"baseline_mode",
	"gl_entry_count",
	"stock_ledger_entry_count",
	"submitted_sales_invoice_count",
	"validations",
	"warnings",
	"blocking_errors",
)


class SubmittedSalesInvoicePreflightService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, sales_invoice=None):
		invoice_name = sales_invoice or self._find_latest_qa_draft_sales_invoice()
		if not invoice_name:
			self._set_target_mode(None, None)
			self._read_baseline_counts()
			self._apply_baseline_semantics()
			self._block("找不到可檢查的 Draft Sales Invoice。")
			self._set_status()
			return self.report

		self.report["sales_invoice"] = invoice_name
		if not frappe.db.exists("Sales Invoice", invoice_name):
			self._set_target_mode(None, None)
			self._read_baseline_counts()
			self._apply_baseline_semantics()
			self._block(f"Sales Invoice 不存在：{invoice_name}")
			self._set_status()
			return self.report

		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		linked_vehicle = self._resolve_linked_vehicle(invoice_name)
		self._set_target_mode(invoice, linked_vehicle)
		self._read_baseline_counts()
		self._apply_baseline_semantics()
		self._validate_sales_invoice(invoice, linked_vehicle)
		self._validate_item_row(invoice, linked_vehicle)
		self._validate_tax_row(invoice)
		self._validate_warehouse()
		self._validate_accounts()
		self._set_status()
		return self.report

	def _new_report(self):
		return {
			"status": "fail",
			"ready_to_submit": False,
			"company": COMPANY,
			"sales_invoice": None,
			"customer": None,
			"item_code": None,
			"serial_no": None,
			"warehouse": None,
			"income_account": None,
			"expense_account": EXPENSE_ACCOUNT,
			"tax_template": TAX_TEMPLATE,
			"tax_account": TAX_ACCOUNT,
			"target_mode": None,
			"baseline_mode": None,
			"gl_entry_count": None,
			"stock_ledger_entry_count": None,
			"submitted_sales_invoice_count": None,
			"validations": [],
			"warnings": [],
			"blocking_errors": [],
		}

	def _find_latest_qa_draft_sales_invoice(self):
		return frappe.db.get_value(
			"Sales Invoice",
			{
				"company": COMPANY,
				"docstatus": 0,
				"remarks": ["like", f"%{QA_REMARKS_MARKER}%"],
			},
			"name",
			order_by="modified desc",
		)

	def _find_latest_formal_vehicle_sales_invoice(self):
		for vehicle in _get_formal_vehicle_sales_invoice_candidates(limit=50):
			invoice_name = vehicle.get("sales_invoice")
			if invoice_name:
				return invoice_name
		return None

	def _new_not_found_report(self, message):
		self._set_target_mode(None, None)
		self._read_baseline_counts()
		self._apply_baseline_semantics()
		self._block(message)
		self._set_status()
		return self.report

	def _set_target_mode(self, invoice, linked_vehicle):
		if invoice and _is_qa_sales_invoice(invoice):
			self.report["target_mode"] = "qa_draft"
			self.report["baseline_mode"] = "clean_site_expected"
		elif invoice and linked_vehicle and getattr(linked_vehicle, "sales_invoice", None) == invoice.name:
			self.report["target_mode"] = "formal_vehicle_draft"
			self.report["baseline_mode"] = "formal_flow_observe_only"
		else:
			self.report["target_mode"] = "unknown"
			self.report["baseline_mode"] = "clean_site_expected"

	def _read_baseline_counts(self):
		self.report["gl_entry_count"] = frappe.db.count("GL Entry", {"company": COMPANY})
		self.report["stock_ledger_entry_count"] = frappe.db.count("Stock Ledger Entry", {"company": COMPANY})
		self.report["submitted_sales_invoice_count"] = frappe.db.count(
			"Sales Invoice",
			{"company": COMPANY, "docstatus": 1},
		)

		self.report["validations"].append("已讀取 submit 前 GL / Stock Ledger / submitted Sales Invoice baseline counts。")

	def _apply_baseline_semantics(self):
		site = getattr(getattr(frappe, "local", None), "site", None)
		if self.report["baseline_mode"] == "formal_flow_observe_only":
			self.report["validations"].append(
				f"formal flow baseline observed: GL Entry count = {self.report['gl_entry_count']}"
			)
			self.report["validations"].append(
				"formal flow baseline observed: "
				f"Stock Ledger Entry count = {self.report['stock_ledger_entry_count']}"
			)
			if site == EXPECTED_CLEAN_SITE and self.report["submitted_sales_invoice_count"]:
				self._warn(
					"erpnext-coa.test clean baseline warning: submitted Sales Invoice count 已非 0，"
					"會干擾第一張 submitted Sales Invoice QA 判斷；這不是 formal draft payload error。"
				)
			return

		if site == EXPECTED_CLEAN_SITE:
			if self.report["gl_entry_count"]:
				self._warn("erpnext-coa.test 目前預期 GL Entry count 為 0，實際已有資料；本 preflight 不自動修復。")
			if self.report["stock_ledger_entry_count"]:
				self._warn("erpnext-coa.test 目前預期 Stock Ledger Entry count 為 0，實際已有資料；本 preflight 不自動修復。")
			if self.report["submitted_sales_invoice_count"]:
				self._warn("erpnext-coa.test 目前預期 submitted Sales Invoice count 為 0，實際已有資料；本 preflight 不自動修復。")

	def _resolve_linked_vehicle(self, invoice_name):
		vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": invoice_name}, "name")
		if not vehicle_name:
			return None
		return frappe.get_doc("Used Car Vehicle", vehicle_name)

	def _validate_sales_invoice(self, invoice, linked_vehicle):
		self.report["customer"] = getattr(invoice, "customer", None)
		if getattr(invoice, "company", None) != COMPANY:
			self._block(f"Sales Invoice company 必須是 {COMPANY}。")
		if int(getattr(invoice, "docstatus", 0) or 0) != 0:
			self._block("Sales Invoice 必須是 Draft，docstatus 必須為 0。")
		if int(getattr(invoice, "update_stock", 0) or 0) != 1:
			self._block("Sales Invoice update_stock 必須為 1。")
		if not getattr(invoice, "customer", None):
			self._block("Sales Invoice 必須有 customer。")
		elif not frappe.db.exists("Customer", invoice.customer):
			self._block(f"Sales Invoice customer 不存在：{invoice.customer}")
		if getattr(invoice, "taxes_and_charges", None) != TAX_TEMPLATE:
			self._block(f"Sales Invoice taxes_and_charges 必須是 {TAX_TEMPLATE}。")

		remarks = getattr(invoice, "remarks", None) or ""
		if QA_REMARKS_MARKER in remarks:
			self.report["validations"].append("Sales Invoice remarks 包含 P1-ACC-6E QA 標記。")
		elif linked_vehicle and getattr(linked_vehicle, "sales_invoice", None) == invoice.name:
			self.report["validations"].append("Sales Invoice 可由 Used Car Vehicle.sales_invoice 反查正式車輛流程草稿。")
		else:
			self._block("Sales Invoice remarks 缺少 QA 標記，且無法由 Used Car Vehicle.sales_invoice 反查。")

		if not self.report["blocking_errors"]:
			self.report["validations"].append("Sales Invoice header submit preflight 通過。")

	def _validate_item_row(self, invoice, linked_vehicle):
		items = list(getattr(invoice, "items", []) or [])
		if len(items) != 1:
			self._block("Sales Invoice 必須有且只有一筆 item row。")
			return

		row = items[0]
		expected_item_code = getattr(linked_vehicle, "item", None) or ITEM_CODE
		expected_warehouse = getattr(linked_vehicle, "stock_warehouse", None) or WAREHOUSE
		self.report["item_code"] = getattr(row, "item_code", None)
		self.report["serial_no"] = getattr(row, "serial_no", None)
		self.report["warehouse"] = getattr(row, "warehouse", None)
		self.report["income_account"] = getattr(row, "income_account", None)
		self.report["expense_account"] = getattr(row, "expense_account", None) or EXPENSE_ACCOUNT

		if row.item_code != expected_item_code:
			self._block(f"Sales Invoice item_code 必須是 {expected_item_code}。")
		if flt(getattr(row, "qty", 0)) != 1:
			self._block("Sales Invoice item qty 必須為 1。")
		if flt(getattr(row, "rate", 0)) <= 0:
			self._block("Sales Invoice item rate 必須大於 0。")
		if row.warehouse != expected_warehouse:
			self._block(f"Sales Invoice item warehouse 必須是 {expected_warehouse}。")
		if row.income_account != INCOME_ACCOUNT:
			self._block(f"Sales Invoice item income_account 必須是 {INCOME_ACCOUNT}。")

		if not frappe.db.exists("Item", row.item_code):
			self._block(f"Sales Invoice item 不存在：{row.item_code}")
			return

		item = frappe.get_doc("Item", row.item_code)
		if int(getattr(item, "has_serial_no", 0) or 0):
			self._validate_serial_no(row, item)
		else:
			self.report["validations"].append("Item 非 serial item，無需 serial_no submit preflight。")

		self.report["validations"].append("Sales Invoice item row 已完成 submit preflight 檢查。")

	def _validate_serial_no(self, row, item):
		serial_no = getattr(row, "serial_no", None)
		if not serial_no:
			self._block("serial item submit 前必須指定 serial_no。")
			return
		if not frappe.db.exists("Serial No", serial_no):
			self._block(f"Serial No 不存在：{serial_no}")
			return

		serial_doc = frappe.get_doc("Serial No", serial_no)
		if getattr(serial_doc, "item_code", None) != item.name:
			self._block(f"Serial No {serial_no} item_code 必須等於 {item.name}。")

		status = getattr(serial_doc, "status", None)
		if status and status in {"Delivered", "Inactive", "Disabled", "Not Available", "Unavailable", "已交付", "不可用"}:
			self._block(f"Serial No {serial_no} 狀態不可用：{status}")
		elif not status:
			self._warn("Serial No 狀態欄位無法可靠讀取；live submit 前需人工確認序號仍可出庫。")

		warehouse = getattr(serial_doc, "warehouse", None)
		if warehouse and warehouse != getattr(row, "warehouse", None):
			self._block(f"Serial No {serial_no} warehouse 必須等於 item row warehouse。")
		elif not warehouse:
			self._warn("Serial No warehouse 欄位無法可靠讀取；live submit 前需人工確認庫存仍在指定倉庫。")

		self.report["validations"].append("Serial No item_code submit preflight 通過。")

	def _validate_warehouse(self):
		if not frappe.db.exists("Warehouse", WAREHOUSE):
			self._block(f"Warehouse 不存在：{WAREHOUSE}")
			return

		warehouse = frappe.get_doc("Warehouse", WAREHOUSE)
		if getattr(warehouse, "company", None) != COMPANY:
			self._block(f"Warehouse {WAREHOUSE} company 必須是 {COMPANY}。")
		if int(getattr(warehouse, "is_group", 0) or 0):
			self._block(f"Warehouse {WAREHOUSE} 必須是非群組倉庫。")
		if int(getattr(warehouse, "disabled", 0) or 0):
			self._block(f"Warehouse {WAREHOUSE} 不可停用。")
		if getattr(warehouse, "account", None) != INVENTORY_ACCOUNT:
			self._block(f"Warehouse {WAREHOUSE} account 必須是 {INVENTORY_ACCOUNT}。")

		self.report["validations"].append("Warehouse submit preflight 已完成。")

	def _validate_accounts(self):
		for account_name in REQUIRED_ACCOUNTS:
			if not frappe.db.exists("Account", account_name):
				self._block(f"必要 Account 不存在：{account_name}")
				continue

			account = frappe.get_doc("Account", account_name)
			if getattr(account, "company", None) != COMPANY:
				self._block(f"Account {account_name} company 必須是 {COMPANY}。")
			if int(getattr(account, "is_group", 0) or 0):
				self._block(f"Account {account_name} 必須是非 group ledger account。")
			if int(getattr(account, "disabled", 0) or 0):
				self._block(f"Account {account_name} 不可停用。")

		self.report["validations"].append("必要 Account submit preflight 已完成。")

	def _validate_tax_row(self, invoice):
		taxes = list(getattr(invoice, "taxes", []) or [])
		if len(taxes) != 1:
			self._block("Sales Invoice 必須有且只有一筆主要 tax row。")
			return

		row = taxes[0]
		if getattr(row, "charge_type", None) != "On Net Total":
			self._block("Sales Invoice tax row charge_type 必須是 On Net Total。")
		if getattr(row, "account_head", None) != TAX_ACCOUNT:
			self._block(f"Sales Invoice tax row account_head 必須是 {TAX_ACCOUNT}。")
		if flt(getattr(row, "rate", 0)) != 5:
			self._block("Sales Invoice tax row rate 必須是 5。")
		if int(getattr(row, "included_in_print_rate", 0) or 0) != 1:
			self._block("Sales Invoice tax row included_in_print_rate 必須是 1。")

		self.report["validations"].append("Sales Invoice tax row submit preflight 已完成。")

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _warn(self, message):
		self.report["warnings"].append(message)

	def _set_status(self):
		if self.report["blocking_errors"]:
			self.report["status"] = "fail"
		elif self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"

		self.report["ready_to_submit"] = self.report["status"] == "pass"


def _is_qa_sales_invoice(invoice):
	remarks = getattr(invoice, "remarks", None) or ""
	return QA_REMARKS_MARKER in remarks


def _get_formal_vehicle_sales_invoice_candidates(limit=10):
	vehicles = frappe.db.get_all(
		"Used Car Vehicle",
		filters={"sales_invoice": ["is", "set"]},
		fields=("name", "sales_invoice", "status", "formal_delivery_status"),
		order_by="modified desc",
		limit=limit,
	)
	results = []
	for vehicle in vehicles:
		invoice_name = vehicle.get("sales_invoice")
		if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
			continue

		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		if getattr(invoice, "company", None) != COMPANY:
			continue
		if int(getattr(invoice, "docstatus", 0) or 0) != 0:
			continue
		if _is_qa_sales_invoice(invoice):
			continue

		row = (list(getattr(invoice, "items", []) or []) or [None])[0]
		results.append(
			{
				"vehicle": vehicle.get("name"),
				"sales_invoice": invoice_name,
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
				"customer": getattr(invoice, "customer", None),
				"docstatus": getattr(invoice, "docstatus", None),
				"item_code": getattr(row, "item_code", None) if row else None,
				"serial_no": getattr(row, "serial_no", None) if row else None,
				"warehouse": getattr(row, "warehouse", None) if row else None,
				"taxes_and_charges": getattr(invoice, "taxes_and_charges", None),
				"modified": getattr(invoice, "modified", None),
			}
		)
	return results


@frappe.whitelist()
def run_submitted_sales_invoice_preflight(sales_invoice=None):
	return SubmittedSalesInvoicePreflightService().run(sales_invoice=sales_invoice)


@frappe.whitelist()
def run_latest_formal_vehicle_sales_invoice_preflight():
	service = SubmittedSalesInvoicePreflightService()
	invoice_name = service._find_latest_formal_vehicle_sales_invoice()
	if not invoice_name:
		return service._new_not_found_report("找不到正式車輛流程 Draft Sales Invoice。")
	return service.run(sales_invoice=invoice_name)


@frappe.whitelist()
def find_formal_vehicle_sales_invoice_preflight_candidates(limit=10):
	return _get_formal_vehicle_sales_invoice_candidates(limit=limit)
