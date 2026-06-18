import frappe
from frappe.utils import flt, nowdate


COMPANY = "OO"
COMPANY_ABBR = "O"
ITEM_CODE = "USED-CAR-VEHICLE"
ITEM_GROUP = "中古車"
STOCK_UOM = "NOS"
WAREHOUSE = "中古車庫存倉 - O"
INCOME_ACCOUNT = "0100001-UC - 中古車銷售收入 - O"
EXPENSE_ACCOUNT = "0100005-UC - 中古車銷貨成本 - O"
INVENTORY_ACCOUNT = "0201131 - 商品 - O"
RECEIVABLE_ACCOUNT = "0201123 - 應收帳款 - O"
TAX_ACCOUNT = "0202134 - 銷項稅額 - O"
INCLUDED_TAX_TEMPLATE = "台灣營業稅 5%（含稅） - O"
EXCLUDED_TAX_TEMPLATE = "台灣營業稅 5%（未稅） - O"
QA_CUSTOMER_NAME = "P1-ACC-6E QA Customer"
QA_REMARKS = "P1-ACC-6E QA Draft Sales Invoice；不可提交，驗證後可刪除"


REQUIRED_ACCOUNTS = (
	INCOME_ACCOUNT,
	EXPENSE_ACCOUNT,
	INVENTORY_ACCOUNT,
	RECEIVABLE_ACCOUNT,
	TAX_ACCOUNT,
)


COMPANY_DEFAULTS = {
	"default_receivable_account": RECEIVABLE_ACCOUNT,
	"default_income_account": INCOME_ACCOUNT,
	"default_expense_account": EXPENSE_ACCOUNT,
	"default_inventory_account": INVENTORY_ACCOUNT,
}


REPORT_KEYS = (
	"status",
	"company",
	"customer",
	"sales_invoice",
	"item",
	"warehouse",
	"income_account",
	"expense_account",
	"tax_template",
	"tax_account",
	"gl_entry_count_before",
	"gl_entry_count_after",
	"stock_ledger_entry_count_before",
	"stock_ledger_entry_count_after",
	"validations",
	"warnings",
	"errors",
)


class MinimalAccountingStockSetupQAService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, commit=False):
		self._validate_required_setup()
		if self.report["errors"]:
			self._set_status()
			return self.report

		try:
			customer = self._get_or_create_qa_customer()
			self.report["customer"] = customer
			invoice = self._create_draft_sales_invoice(customer)
		except Exception as exc:
			self.report["errors"].append(f"Draft Sales Invoice creation blocked by ERPNext validation: {exc}")
			self._set_status()
			return self.report

		self.report["sales_invoice"] = invoice.name
		self._validate_draft_sales_invoice(invoice)
		self._validate_after_counts()
		self._set_status()

		if commit and self.report["status"] in ("pass", "warning"):
			frappe.db.commit()
		elif commit:
			frappe.db.rollback()

		return self.report

	def _new_report(self):
		return {
			"status": "fail",
			"company": COMPANY,
			"customer": None,
			"sales_invoice": None,
			"item": ITEM_CODE,
			"warehouse": WAREHOUSE,
			"income_account": INCOME_ACCOUNT,
			"expense_account": EXPENSE_ACCOUNT,
			"tax_template": INCLUDED_TAX_TEMPLATE,
			"tax_account": TAX_ACCOUNT,
			"gl_entry_count_before": None,
			"gl_entry_count_after": None,
			"stock_ledger_entry_count_before": None,
			"stock_ledger_entry_count_after": None,
			"validations": [],
			"warnings": [],
			"errors": [],
		}

	def _validate_required_setup(self):
		self._validate_company()
		self._validate_clean_ledger_counts_before()
		self._validate_accounts()
		self._validate_company_defaults()
		self._validate_warehouse()
		self._validate_item()
		self._validate_tax_template(INCLUDED_TAX_TEMPLATE, included_in_print_rate=1, required=True)
		self._validate_tax_template(EXCLUDED_TAX_TEMPLATE, included_in_print_rate=0, required=False)

	def _validate_company(self):
		if not frappe.db.exists("Company", COMPANY):
			self.report["errors"].append(f"Company {COMPANY} does not exist.")
			return

		abbr = frappe.db.get_value("Company", COMPANY, "abbr")
		if abbr != COMPANY_ABBR:
			self.report["errors"].append(f"Company {COMPANY} abbreviation must be {COMPANY_ABBR}.")
			return

		self.report["validations"].append("Company OO exists with abbreviation O.")

	def _validate_clean_ledger_counts_before(self):
		gl_count = frappe.db.count("GL Entry", {"company": COMPANY})
		sle_count = frappe.db.count("Stock Ledger Entry", {"company": COMPANY})
		self.report["gl_entry_count_before"] = gl_count
		self.report["stock_ledger_entry_count_before"] = sle_count

		if gl_count:
			self.report["errors"].append("GL Entry count must be 0 before creating QA draft.")
		if sle_count:
			self.report["errors"].append("Stock Ledger Entry count must be 0 before creating QA draft.")
		if not gl_count and not sle_count:
			self.report["validations"].append("GL Entry and Stock Ledger Entry counts are 0 before draft creation.")

	def _validate_accounts(self):
		for account_name in REQUIRED_ACCOUNTS:
			if not frappe.db.exists("Account", account_name):
				self.report["errors"].append(f"Required Account missing: {account_name}")
				continue

			account = frappe.get_doc("Account", account_name)
			if account.company != COMPANY:
				self.report["errors"].append(f"Account {account_name} must belong to {COMPANY}.")
			if int(account.is_group or 0):
				self.report["errors"].append(f"Account {account_name} must be a ledger account, not a group.")
			if int(account.disabled or 0):
				self.report["errors"].append(f"Account {account_name} must not be disabled.")

		if not any(error.startswith("Required Account") or error.startswith("Account ") for error in self.report["errors"]):
			self.report["validations"].append("Required accounts exist and are active ledger accounts for OO.")

	def _validate_company_defaults(self):
		company = frappe.get_doc("Company", COMPANY)
		for fieldname, expected in COMPANY_DEFAULTS.items():
			actual = getattr(company, fieldname, None)
			if actual != expected:
				self.report["errors"].append(f"Company {fieldname} must be {expected}; found {actual}.")

		if not any(error.startswith("Company default_") for error in self.report["errors"]):
			self.report["validations"].append("Company default accounting accounts match P1-ACC-6E requirements.")

	def _validate_warehouse(self):
		if not frappe.db.exists("Warehouse", WAREHOUSE):
			self.report["errors"].append(f"Warehouse missing: {WAREHOUSE}")
			return

		warehouse = frappe.get_doc("Warehouse", WAREHOUSE)
		if warehouse.company != COMPANY:
			self.report["errors"].append(f"Warehouse {WAREHOUSE} must belong to {COMPANY}.")
		if int(warehouse.is_group or 0):
			self.report["errors"].append(f"Warehouse {WAREHOUSE} must not be a group.")
		if int(getattr(warehouse, "disabled", 0) or 0):
			self.report["errors"].append(f"Warehouse {WAREHOUSE} must not be disabled.")
		if warehouse.account != INVENTORY_ACCOUNT:
			self.report["errors"].append(f"Warehouse {WAREHOUSE} account must be {INVENTORY_ACCOUNT}.")

		if not any(error.startswith("Warehouse ") for error in self.report["errors"]):
			self.report["validations"].append("Warehouse is active, non-group, and linked to the inventory account.")

	def _validate_item(self):
		if not frappe.db.exists("Item", ITEM_CODE):
			self.report["errors"].append(f"Item missing: {ITEM_CODE}")
			return

		item = frappe.get_doc("Item", ITEM_CODE)
		expected_fields = {
			"item_group": ITEM_GROUP,
			"stock_uom": STOCK_UOM,
			"is_stock_item": 1,
			"is_sales_item": 1,
			"is_purchase_item": 1,
			"has_serial_no": 1,
			"disabled": 0,
		}
		for fieldname, expected in expected_fields.items():
			actual = getattr(item, fieldname, None)
			if fieldname in {"is_stock_item", "is_sales_item", "is_purchase_item", "has_serial_no", "disabled"}:
				actual = int(actual or 0)
			if actual != expected:
				self.report["errors"].append(f"Item {ITEM_CODE} {fieldname} must be {expected}; found {actual}.")

		item_default = self._find_child_for_company(item, "item_defaults")
		if not item_default:
			self.report["errors"].append(f"Item {ITEM_CODE} must have Item Default for company {COMPANY}.")
			return

		default_checks = {
			"default_warehouse": WAREHOUSE,
			"income_account": INCOME_ACCOUNT,
			"expense_account": EXPENSE_ACCOUNT,
		}
		for fieldname, expected in default_checks.items():
			actual = getattr(item_default, fieldname, None)
			if actual != expected:
				self.report["errors"].append(f"Item Default {fieldname} must be {expected}; found {actual}.")

		if not any(error.startswith(f"Item {ITEM_CODE}") or error.startswith("Item Default ") for error in self.report["errors"]):
			self.report["validations"].append("Item and Item Default match P1-ACC-6E requirements.")

	def _validate_tax_template(self, template_name, included_in_print_rate, required):
		if not frappe.db.exists("Sales Taxes and Charges Template", template_name):
			message = f"Sales Taxes and Charges Template missing: {template_name}"
			if required:
				self.report["errors"].append(message)
			else:
				self.report["warnings"].append(message)
			return

		template = frappe.get_doc("Sales Taxes and Charges Template", template_name)
		if template.company != COMPANY:
			self.report["errors"].append(f"Tax template {template_name} must belong to {COMPANY}.")
		if int(getattr(template, "disabled", 0) or 0):
			self.report["errors"].append(f"Tax template {template_name} must not be disabled.")

		taxes = list(getattr(template, "taxes", []) or [])
		if len(taxes) != 1:
			self.report["errors"].append(f"Tax template {template_name} must have exactly one tax row.")
			return

		row = taxes[0]
		if row.charge_type != "On Net Total":
			self.report["errors"].append(f"Tax template {template_name} charge_type must be On Net Total.")
		if row.account_head != TAX_ACCOUNT:
			self.report["errors"].append(f"Tax template {template_name} account_head must be {TAX_ACCOUNT}.")
		if flt(row.rate) != 5:
			self.report["errors"].append(f"Tax template {template_name} rate must be 5.")
		if int(getattr(row, "included_in_print_rate", 0) or 0) != included_in_print_rate:
			self.report["errors"].append(
				f"Tax template {template_name} included_in_print_rate must be {included_in_print_rate}."
			)

		if required and not any(error.startswith(f"Tax template {template_name}") for error in self.report["errors"]):
			self.report["validations"].append("Included Taiwan 5% Sales Taxes and Charges Template is valid.")

	def _get_or_create_qa_customer(self):
		existing = frappe.db.get_value("Customer", {"customer_name": QA_CUSTOMER_NAME}, "name")
		if existing:
			return existing

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": QA_CUSTOMER_NAME,
				"customer_type": "Individual",
				"customer_group": self._resolve_leaf_value("Customer Group"),
				"territory": self._resolve_leaf_value("Territory"),
			}
		)
		customer.insert(ignore_permissions=True)
		return customer.name

	def _resolve_leaf_value(self, doctype):
		value = frappe.db.get_value(doctype, {"is_group": 0}, "name", order_by="name asc")
		if not value:
			frappe.throw(f"Cannot find non-group {doctype} for QA Customer.")
		return value

	def _create_draft_sales_invoice(self, customer):
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": COMPANY,
				"customer": customer,
				"posting_date": nowdate(),
				"update_stock": 1,
				"taxes_and_charges": INCLUDED_TAX_TEMPLATE,
				"remarks": QA_REMARKS,
				"items": [
					{
						"item_code": ITEM_CODE,
						"qty": 1,
						"rate": 1000000,
						"warehouse": WAREHOUSE,
						"income_account": INCOME_ACCOUNT,
					}
				],
				"taxes": [self._build_tax_row_from_template()],
			}
		)
		invoice.insert(ignore_permissions=True)
		return invoice

	def _build_tax_row_from_template(self):
		template = frappe.get_doc("Sales Taxes and Charges Template", INCLUDED_TAX_TEMPLATE)
		row = template.taxes[0]
		return {
			"charge_type": row.charge_type,
			"account_head": row.account_head,
			"rate": row.rate,
			"included_in_print_rate": row.included_in_print_rate,
			"description": getattr(row, "description", None) or "營業稅 5%（含稅）",
		}

	def _validate_draft_sales_invoice(self, invoice):
		if int(invoice.docstatus or 0) != 0:
			self.report["errors"].append("Sales Invoice must remain draft with docstatus 0.")

		item = (invoice.items or [None])[0]
		if not item:
			self.report["errors"].append("Sales Invoice must contain one item row.")
			return
		if item.item_code != ITEM_CODE:
			self.report["errors"].append(f"Sales Invoice item_code must be {ITEM_CODE}.")
		if item.warehouse != WAREHOUSE:
			self.report["errors"].append(f"Sales Invoice item warehouse must be {WAREHOUSE}.")
		if item.income_account != INCOME_ACCOUNT:
			self.report["errors"].append(f"Sales Invoice item income_account must be {INCOME_ACCOUNT}.")
		if getattr(item, "expense_account", None) and item.expense_account != EXPENSE_ACCOUNT:
			self.report["errors"].append(f"Sales Invoice item expense_account must be {EXPENSE_ACCOUNT}.")
		if not getattr(item, "expense_account", None):
			self.report["warnings"].append("Sales Invoice draft item expense_account is empty at draft stage.")

		tax = (invoice.taxes or [None])[0]
		if not tax:
			self.report["errors"].append("Sales Invoice must contain one tax row.")
			return
		if tax.account_head != TAX_ACCOUNT:
			self.report["errors"].append(f"Sales Invoice tax account_head must be {TAX_ACCOUNT}.")
		if flt(tax.rate) != 5:
			self.report["errors"].append("Sales Invoice tax rate must be 5.")
		if int(getattr(tax, "included_in_print_rate", 0) or 0) != 1:
			self.report["errors"].append("Sales Invoice tax included_in_print_rate must be 1.")

		if not any(error.startswith("Sales Invoice ") for error in self.report["errors"]):
			self.report["validations"].append("Draft Sales Invoice was created and remains unsubmitted.")

	def _validate_after_counts(self):
		gl_count = frappe.db.count("GL Entry", {"company": COMPANY})
		sle_count = frappe.db.count("Stock Ledger Entry", {"company": COMPANY})
		self.report["gl_entry_count_after"] = gl_count
		self.report["stock_ledger_entry_count_after"] = sle_count

		if gl_count:
			self.report["errors"].append("GL Entry count must remain 0 after creating QA draft.")
		if sle_count:
			self.report["errors"].append("Stock Ledger Entry count must remain 0 after creating QA draft.")
		if not gl_count and not sle_count:
			self.report["validations"].append("GL Entry and Stock Ledger Entry counts remain 0 after draft creation.")

	def _find_child_for_company(self, doc, table_fieldname):
		for child in getattr(doc, table_fieldname, []) or []:
			if getattr(child, "company", None) == COMPANY:
				return child
		return None

	def _set_status(self):
		if self.report["errors"]:
			self.report["status"] = "fail"
		elif self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"


@frappe.whitelist()
def run_minimal_accounting_stock_setup_qa(commit=1):
	commit = bool(int(commit)) if isinstance(commit, str) else bool(commit)
	return MinimalAccountingStockSetupQAService().run(commit=commit)
