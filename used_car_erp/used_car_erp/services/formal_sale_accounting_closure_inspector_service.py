import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.advance_settlement_readiness_service import ADVANCE_ACCOUNT_KEYWORDS
from used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service import (
	COMPANY,
	EXPENSE_ACCOUNT,
	INCOME_ACCOUNT,
	INVENTORY_ACCOUNT,
	RECEIVABLE_ACCOUNT,
	TAX_ACCOUNT,
	TAX_TEMPLATE,
)


ROUNDING_TOLERANCE = 0.01
REQUIRED_SALES_INVOICE_GL_ACCOUNTS = (RECEIVABLE_ACCOUNT, INCOME_ACCOUNT, TAX_ACCOUNT, INVENTORY_ACCOUNT, EXPENSE_ACCOUNT)

REPORT_KEYS = (
	"status",
	"closed",
	"ready_for_ui_review",
	"company",
	"vehicle",
	"vehicle_status",
	"formal_delivery_status",
	"sales_invoice",
	"sales_invoice_docstatus",
	"sales_invoice_grand_total",
	"sales_invoice_outstanding_amount",
	"sales_invoice_gl_entry_count",
	"sales_invoice_stock_ledger_entry_count",
	"sales_invoice_gl_accounts",
	"sales_invoice_sle_rows",
	"reservation",
	"customer",
	"deposit_money_flow",
	"deposit_amount",
	"deposit_voucher_draft",
	"deposit_journal_entry",
	"deposit_advance_account",
	"final_money_flow",
	"final_amount",
	"final_voucher_draft",
	"final_journal_entry",
	"final_advance_account",
	"advance_total",
	"advance_settlement_journal_entry",
	"advance_settlement_journal_entry_docstatus",
	"advance_settlement_gl_entry_count",
	"advance_settlement_gl_accounts",
	"payment_entry_count",
	"delivery_note_count",
	"purchase_invoice_count",
	"unexpected_journal_entry_count",
	"unexpected_stock_entry_count",
	"purchase_price",
	"serial_no",
	"serial_status",
	"serial_warehouse",
	"amount_summary",
	"validations",
	"warnings",
	"blocking_errors",
)

SIDE_EFFECT_LINK_FIELDS = {
	"Payment Entry": "reference_name",
	"Delivery Note": "against_sales_invoice",
	"Purchase Invoice": "bill_no",
	"Stock Entry": "sales_invoice_no",
}


class FormalSaleAccountingClosureInspectorService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, sales_invoice=None, vehicle_name=None):
		vehicle = self._resolve_target_vehicle(sales_invoice=sales_invoice, vehicle_name=vehicle_name)
		if not vehicle:
			self._block("找不到符合條件的正式售車會計閉環檢查 target。")
			self._set_status()
			return self.report

		invoice = self._resolve_target_invoice(vehicle, sales_invoice=sales_invoice)
		settlement = self._resolve_settlement_journal(vehicle)
		self._read_vehicle(vehicle)
		self._read_invoice(invoice)
		reservation = self._read_reservation(vehicle)
		self._validate_vehicle_gate(vehicle, invoice, settlement, reservation)
		self._validate_reservation_gate(reservation, vehicle, invoice)
		self._validate_flow_bundle(vehicle, reservation, "deposit", "訂金", "訂金收款")
		self._validate_flow_bundle(vehicle, reservation, "final", "尾款", "尾款收款")
		self._validate_sales_invoice_gate(invoice)
		self._validate_sales_invoice_gl_and_sle(invoice)
		self._validate_advance_settlement_gate(settlement)
		self._validate_non_goal_side_effects()
		self._validate_amounts()
		self._build_amount_summary()
		self._set_status()
		return self.report

	def find_candidates(self, limit=10):
		return _get_formal_sale_accounting_closure_candidates(limit=limit)

	def _new_report(self):
		list_keys = {"sales_invoice_gl_accounts", "sales_invoice_sle_rows", "advance_settlement_gl_accounts", "validations", "warnings", "blocking_errors"}
		return {key: [] if key in list_keys else None for key in REPORT_KEYS} | {
			"status": "fail",
			"closed": False,
			"ready_for_ui_review": False,
			"company": COMPANY,
			"sales_invoice_grand_total": 0,
			"sales_invoice_outstanding_amount": 0,
			"sales_invoice_gl_entry_count": 0,
			"sales_invoice_stock_ledger_entry_count": 0,
			"deposit_amount": 0,
			"final_amount": 0,
			"advance_total": 0,
			"advance_settlement_journal_entry_docstatus": 0,
			"advance_settlement_gl_entry_count": 0,
			"payment_entry_count": 0,
			"delivery_note_count": 0,
			"purchase_invoice_count": 0,
			"unexpected_journal_entry_count": 0,
			"unexpected_stock_entry_count": 0,
			"purchase_price": 0,
			"amount_summary": {},
		}

	def _resolve_target_vehicle(self, sales_invoice=None, vehicle_name=None):
		if vehicle_name:
			self.report["vehicle"] = vehicle_name
			if frappe.db.exists("Used Car Vehicle", vehicle_name):
				return frappe.get_doc("Used Car Vehicle", vehicle_name)
			return None
		if sales_invoice:
			self.report["sales_invoice"] = sales_invoice
			vehicle = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": sales_invoice}, "name")
			return frappe.get_doc("Used Car Vehicle", vehicle) if vehicle and frappe.db.exists("Used Car Vehicle", vehicle) else None
		candidates = self.find_candidates(limit=1)
		vehicle = candidates[0].get("vehicle") if candidates else None
		return frappe.get_doc("Used Car Vehicle", vehicle) if vehicle and frappe.db.exists("Used Car Vehicle", vehicle) else None

	def _resolve_target_invoice(self, vehicle, sales_invoice=None):
		invoice_name = sales_invoice or vehicle.get("sales_invoice")
		self.report["sales_invoice"] = invoice_name
		return frappe.get_doc("Sales Invoice", invoice_name) if invoice_name and frappe.db.exists("Sales Invoice", invoice_name) else None

	def _resolve_settlement_journal(self, vehicle):
		journal_entry = vehicle.get("advance_settlement_journal_entry") if vehicle else None
		self.report["advance_settlement_journal_entry"] = journal_entry
		return frappe.get_doc("Journal Entry", journal_entry) if journal_entry and frappe.db.exists("Journal Entry", journal_entry) else None

	def _read_vehicle(self, vehicle):
		self.report.update(
			{
				"vehicle": vehicle.get("name"),
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
				"reservation": vehicle.get("completed_reservation"),
				"deposit_money_flow": vehicle.get("deposit_money_flow"),
				"deposit_voucher_draft": vehicle.get("deposit_voucher_draft"),
				"deposit_journal_entry": vehicle.get("deposit_journal_entry"),
				"final_money_flow": vehicle.get("final_money_flow"),
				"final_voucher_draft": vehicle.get("final_voucher_draft"),
				"final_journal_entry": vehicle.get("final_journal_entry"),
				"advance_settlement_journal_entry": vehicle.get("advance_settlement_journal_entry"),
				"purchase_price": flt(vehicle.get("purchase_price")),
			}
		)

	def _read_invoice(self, invoice):
		if not invoice:
			return
		self.report.update(
			{
				"company": getattr(invoice, "company", None),
				"customer": getattr(invoice, "customer", None),
				"sales_invoice_docstatus": int(getattr(invoice, "docstatus", 0) or 0),
				"sales_invoice_grand_total": flt(getattr(invoice, "grand_total", 0)),
				"sales_invoice_outstanding_amount": flt(getattr(invoice, "outstanding_amount", 0)),
			}
		)

	def _read_reservation(self, vehicle):
		reservation_name = vehicle.get("completed_reservation")
		if not reservation_name or not frappe.db.exists("Used Car Reservation", reservation_name):
			return None
		return frappe.get_doc("Used Car Reservation", reservation_name)

	def _validate_vehicle_gate(self, vehicle, invoice, settlement, reservation):
		if vehicle.get("status") != "已售出":
			self._block("Used Car Vehicle status 必須是 已售出。")
		if vehicle.get("formal_delivery_status") != "已完成":
			self._block("Used Car Vehicle formal_delivery_status 必須是 已完成。")
		if not vehicle.get("sales_invoice"):
			self._block("Used Car Vehicle 缺少 sales_invoice。")
		if not vehicle.get("advance_settlement_journal_entry"):
			self._block("Used Car Vehicle 缺少 advance_settlement_journal_entry。")
		if invoice and vehicle.get("sales_invoice") != invoice.name:
			self._block("Used Car Vehicle.sales_invoice 必須等於 target Sales Invoice。")
		if settlement and vehicle.get("advance_settlement_journal_entry") != settlement.name:
			self._block("Used Car Vehicle.advance_settlement_journal_entry 必須等於 target settlement JE。")
		if not reservation:
			self._block("缺少已完成保留單 completed_reservation。")
		for fieldname, label in (
			("deposit_money_flow", "訂金金流"),
			("deposit_voucher_draft", "訂金傳票草稿"),
			("deposit_journal_entry", "訂金 Journal Entry"),
			("final_money_flow", "尾款金流"),
			("final_voucher_draft", "尾款傳票草稿"),
			("final_journal_entry", "尾款 Journal Entry"),
		):
			if not vehicle.get(fieldname):
				self._block(f"Used Car Vehicle 缺少 {label} 連結。")

	def _validate_reservation_gate(self, reservation, vehicle, invoice):
		if not reservation:
			return
		self.report["reservation"] = reservation.name
		if reservation.get("status") != "已完成":
			self._block("completed_reservation 狀態必須是 已完成。")
		if reservation.get("vehicle") != vehicle.name:
			self._block("completed_reservation.vehicle 必須對應 Used Car Vehicle。")
		if invoice and reservation.get("customer") != getattr(invoice, "customer", None):
			self._block("completed_reservation customer 必須對應 Sales Invoice customer。")
		for reservation_field, vehicle_field, label in (
			("money_flow", "deposit_money_flow", "訂金金流"),
			("voucher_draft", "deposit_voucher_draft", "訂金傳票草稿"),
			("journal_entry", "deposit_journal_entry", "訂金 Journal Entry"),
			("final_money_flow", "final_money_flow", "尾款金流"),
			("final_voucher_draft", "final_voucher_draft", "尾款傳票草稿"),
			("final_journal_entry", "final_journal_entry", "尾款 Journal Entry"),
		):
			if reservation.get(reservation_field) and reservation.get(reservation_field) != vehicle.get(vehicle_field):
				self._block(f"completed_reservation {label} 連結必須對應 Vehicle。")

	def _validate_flow_bundle(self, vehicle, reservation, prefix, label, flow_type):
		money_flow = self._get_required_doc("Used Car Money Flow", vehicle.get(f"{prefix}_money_flow"), f"{label}金流")
		voucher = self._get_required_doc("Used Car Voucher Draft", vehicle.get(f"{prefix}_voucher_draft"), f"{label}傳票草稿")
		journal_entry = self._get_required_doc("Journal Entry", vehicle.get(f"{prefix}_journal_entry"), f"{label} Journal Entry")
		if money_flow:
			self._validate_money_flow(money_flow, reservation, vehicle, label, flow_type)
			self.report[f"{prefix}_amount"] = flt(money_flow.get("amount"))
		if voucher:
			self._validate_voucher_draft(voucher, money_flow, reservation, vehicle, label)
		if journal_entry:
			self._validate_receipt_journal_entry(journal_entry, voucher, label, prefix)

	def _get_required_doc(self, doctype, name, label):
		if not name:
			self._block(f"缺少{label}。")
			return None
		if not frappe.db.exists(doctype, name):
			self._block(f"{label}不存在：{name}")
			return None
		return frappe.get_doc(doctype, name)

	def _validate_money_flow(self, money_flow, reservation, vehicle, label, flow_type):
		if money_flow.get("status") != "已入帳":
			self._block(f"{label}金流 status 必須是 已入帳。")
		if money_flow.get("flow_type") != flow_type:
			self._block(f"{label}金流 flow_type 必須是 {flow_type}。")
		if flt(money_flow.get("amount")) <= 0:
			self._block(f"{label}金流 amount 必須大於 0。")
		if not money_flow.get("journal_entry"):
			self._block(f"{label}金流缺少 journal_entry。")
		if not money_flow.get("voucher_draft"):
			self._block(f"{label}金流缺少 voucher_draft。")
		self._validate_common_links(money_flow, reservation, vehicle, f"{label}金流")

	def _validate_voucher_draft(self, voucher, money_flow, reservation, vehicle, label):
		if voucher.get("status") != "已入帳":
			self._block(f"{label}傳票草稿 status 必須是 已入帳。")
		if money_flow and voucher.get("money_flow") != money_flow.name:
			self._block(f"{label}傳票草稿 money_flow 必須對應金流。")
		if money_flow and voucher.get("journal_entry") != money_flow.get("journal_entry"):
			self._block(f"{label}傳票草稿 journal_entry 必須對應金流。")
		if not list(voucher.get("lines") or []):
			self._block(f"{label}傳票草稿缺少 lines。")
		self._validate_common_links(voucher, reservation, vehicle, f"{label}傳票草稿")

	def _validate_receipt_journal_entry(self, journal_entry, voucher, label, prefix):
		if int(journal_entry.get("docstatus") or 0) != 1:
			self._block(f"{label} Journal Entry docstatus 必須是 1。")
		if journal_entry.get("company") != COMPANY:
			self._block(f"{label} Journal Entry company 必須是 {COMPANY}。")
		accounts = list(journal_entry.get("accounts") or [])
		debit, credit = self._journal_totals(accounts)
		if flt(debit, 2) != flt(credit, 2):
			self._block(f"{label} Journal Entry debit / credit 不平。")
		if not self._resolve_cash_or_bank_account(accounts):
			self._block(f"{label} Journal Entry 無法解析 cash/bank account。")
		advance_account = self._resolve_advance_account(voucher, accounts, credit=True)
		self.report[f"{prefix}_advance_account"] = advance_account
		if not advance_account:
			self._block(f"{label} Journal Entry 無法解析預收 / 暫收 / 負債 account。")
		if journal_entry.name:
			gl_entries = self._read_gl_entries("Journal Entry", journal_entry.name)
			if not gl_entries:
				self._block(f"{label} Journal Entry 找不到對應 GL Entry。")

	def _validate_sales_invoice_gate(self, invoice):
		if not invoice:
			self._block(f"Sales Invoice 不存在：{self.report.get('sales_invoice')}")
			return
		if int(getattr(invoice, "docstatus", 0) or 0) != 1:
			self._block("Sales Invoice docstatus 必須是 1。")
		if getattr(invoice, "company", None) != COMPANY:
			self._block(f"Sales Invoice company 必須是 {COMPANY}。")
		if not getattr(invoice, "customer", None):
			self._block("Sales Invoice 缺少 customer。")
		if int(getattr(invoice, "update_stock", 0) or 0) != 1:
			self._block("Sales Invoice update_stock 必須為 1。")
		if flt(getattr(invoice, "grand_total", 0)) <= 0:
			self._block("Sales Invoice grand_total 必須大於 0。")
		if abs(flt(getattr(invoice, "outstanding_amount", 0))) > ROUNDING_TOLERANCE:
			self._block("Sales Invoice outstanding_amount 必須為 0。")
		self._validate_sales_invoice_items(invoice)
		self._validate_sales_invoice_taxes(invoice)

	def _validate_sales_invoice_items(self, invoice):
		items = list(getattr(invoice, "items", []) or [])
		if len(items) != 1:
			self._block("Sales Invoice item row 必須剛好一筆。")
			return
		row = items[0]
		self.report["serial_no"] = getattr(row, "serial_no", None)
		for fieldname in ("serial_no", "warehouse", "income_account", "expense_account"):
			if not getattr(row, fieldname, None):
				self._block(f"Sales Invoice item row 缺少 {fieldname}。")
		if getattr(row, "income_account", None) != INCOME_ACCOUNT:
			self._block(f"Sales Invoice item income_account 必須是 {INCOME_ACCOUNT}。")
		if getattr(row, "expense_account", None) != EXPENSE_ACCOUNT:
			self._block(f"Sales Invoice item expense_account 必須是 {EXPENSE_ACCOUNT}。")
		self._read_serial_snapshot(getattr(row, "serial_no", None))

	def _validate_sales_invoice_taxes(self, invoice):
		if getattr(invoice, "taxes_and_charges", None) != TAX_TEMPLATE:
			self._block(f"Sales Invoice taxes_and_charges 必須是 {TAX_TEMPLATE}。")
		taxes = list(getattr(invoice, "taxes", []) or [])
		if len(taxes) != 1:
			self._block("Sales Invoice tax row 必須剛好一筆。")
			return
		row = taxes[0]
		if getattr(row, "account_head", None) != TAX_ACCOUNT:
			self._block(f"Sales Invoice tax row account_head 必須是 {TAX_ACCOUNT}。")
		if flt(getattr(row, "rate", 0)) != 5:
			self._block("Sales Invoice tax row rate 必須是 5。")
		if int(getattr(row, "included_in_print_rate", 0) or 0) != 1:
			self._block("Sales Invoice tax row included_in_print_rate 必須是 1。")

	def _validate_sales_invoice_gl_and_sle(self, invoice):
		if not invoice:
			return
		gl_entries = self._read_gl_entries("Sales Invoice", invoice.name)
		self.report["sales_invoice_gl_accounts"] = gl_entries
		self.report["sales_invoice_gl_entry_count"] = len(gl_entries)
		if not gl_entries:
			self._block("找不到 Sales Invoice 對應 GL Entry。")
		accounts = {row.get("account") for row in gl_entries}
		for account in REQUIRED_SALES_INVOICE_GL_ACCOUNTS:
			if account not in accounts:
				self._block(f"Sales Invoice GL Entry 缺少 account：{account}")
		debit = sum(flt(row.get("debit")) for row in gl_entries)
		credit = sum(flt(row.get("credit")) for row in gl_entries)
		if flt(debit, 2) != flt(credit, 2):
			self._block("Sales Invoice GL Entry debit / credit 不平。")
		sle_rows = self._read_sle_rows(invoice.name)
		self.report["sales_invoice_sle_rows"] = sle_rows
		self.report["sales_invoice_stock_ledger_entry_count"] = len(sle_rows)
		if not sle_rows:
			self._block("找不到 Sales Invoice 對應 Stock Ledger Entry。")
		elif not any(flt(row.get("actual_qty")) < 0 for row in sle_rows) and sum(flt(row.get("actual_qty")) for row in sle_rows) >= 0:
			self._block("Sales Invoice Stock Ledger Entry actual_qty 必須有負數或總和小於 0。")

	def _validate_advance_settlement_gate(self, settlement):
		if not settlement:
			self._block(f"Advance Settlement Journal Entry 不存在：{self.report.get('advance_settlement_journal_entry')}")
			return
		self.report["advance_settlement_journal_entry_docstatus"] = int(settlement.get("docstatus") or 0)
		if int(settlement.get("docstatus") or 0) != 1:
			self._block("Advance Settlement Journal Entry docstatus 必須是 1。")
		if settlement.get("company") != COMPANY:
			self._block(f"Advance Settlement Journal Entry company 必須是 {COMPANY}。")
		gl_entries = self._read_gl_entries("Journal Entry", settlement.name)
		self.report["advance_settlement_gl_accounts"] = gl_entries
		self.report["advance_settlement_gl_entry_count"] = len(gl_entries)
		if not gl_entries:
			self._block("找不到 Advance Settlement Journal Entry 對應 GL Entry。")
		debit = sum(flt(row.get("debit")) for row in gl_entries)
		credit = sum(flt(row.get("credit")) for row in gl_entries)
		if flt(debit, 2) != flt(credit, 2):
			self._block("Advance Settlement Journal Entry GL debit / credit 不平。")
		if not any(flt(row.get("debit")) > 0 and self._is_advance_account(row.get("account")) for row in gl_entries):
			self._block("Advance Settlement Journal Entry debit account 必須是預收 / 暫收 / liability account。")
		if not any(flt(row.get("credit")) > 0 and row.get("account") == RECEIVABLE_ACCOUNT for row in gl_entries):
			self._block(f"Advance Settlement Journal Entry credit account 必須是 {RECEIVABLE_ACCOUNT}。")

	def _validate_non_goal_side_effects(self):
		target = self.report.get("sales_invoice")
		if not target:
			return
		for doctype, key in (
			("Payment Entry", "payment_entry_count"),
			("Delivery Note", "delivery_note_count"),
			("Purchase Invoice", "purchase_invoice_count"),
			("Stock Entry", "unexpected_stock_entry_count"),
		):
			count = self._count_optional_target_link(doctype, target)
			self.report[key] = count
			if count:
				self._block(f"target Sales Invoice 不應有 linked {doctype}。")
		self.report["unexpected_journal_entry_count"] = self._count_unexpected_journal_entries(target)
		if self.report["unexpected_journal_entry_count"]:
			self._block("target Sales Invoice 不應有非 settlement 的 linked Journal Entry。")

	def _validate_amounts(self):
		self.report["advance_total"] = flt(self.report.get("deposit_amount")) + flt(self.report.get("final_amount"))
		grand_total = flt(self.report.get("sales_invoice_grand_total"))
		settlement_debit = sum(flt(row.get("debit")) for row in self.report.get("advance_settlement_gl_accounts") or [])
		if abs(settlement_debit - grand_total) > ROUNDING_TOLERANCE:
			self._block("Advance Settlement Journal Entry amount total 必須等於 Sales Invoice grand_total。")
		if abs(settlement_debit - flt(self.report.get("advance_total"))) > ROUNDING_TOLERANCE:
			self._block("Advance Settlement Journal Entry amount total 必須等於 deposit amount + final amount。")

	def _build_amount_summary(self):
		self.report["amount_summary"] = {
			"purchase_price": flt(self.report.get("purchase_price")),
			"deposit_amount": flt(self.report.get("deposit_amount")),
			"final_amount": flt(self.report.get("final_amount")),
			"advance_total": flt(self.report.get("advance_total")),
			"sales_invoice_grand_total": flt(self.report.get("sales_invoice_grand_total")),
			"sales_invoice_outstanding_amount": flt(self.report.get("sales_invoice_outstanding_amount")),
			"sales_invoice_gl_debit_total": sum(flt(row.get("debit")) for row in self.report.get("sales_invoice_gl_accounts") or []),
			"sales_invoice_gl_credit_total": sum(flt(row.get("credit")) for row in self.report.get("sales_invoice_gl_accounts") or []),
			"settlement_je_debit_total": sum(flt(row.get("debit")) for row in self.report.get("advance_settlement_gl_accounts") or []),
			"settlement_je_credit_total": sum(flt(row.get("credit")) for row in self.report.get("advance_settlement_gl_accounts") or []),
		}

	def _validate_common_links(self, doc, reservation, vehicle, label):
		if reservation and doc.get("reservation") and doc.get("reservation") != reservation.name:
			self._block(f"{label} reservation 必須對應 completed_reservation。")
		if doc.get("vehicle") and doc.get("vehicle") != vehicle.name:
			self._block(f"{label} vehicle 必須對應 Used Car Vehicle。")
		if self.report.get("customer") and doc.get("customer") and doc.get("customer") != self.report["customer"]:
			self._block(f"{label} customer 必須對應 Sales Invoice customer。")

	def _read_gl_entries(self, voucher_type, voucher_no):
		return [
			{"account": row.get("account"), "debit": flt(row.get("debit")), "credit": flt(row.get("credit"))}
			for row in frappe.db.get_all(
				"GL Entry",
				filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
				fields=("account", "debit", "credit"),
				order_by="account asc",
			)
		]

	def _read_sle_rows(self, invoice_name):
		return [
			{
				"item_code": row.get("item_code"),
				"warehouse": row.get("warehouse"),
				"actual_qty": flt(row.get("actual_qty")),
				"stock_value_difference": flt(row.get("stock_value_difference")),
			}
			for row in frappe.db.get_all(
				"Stock Ledger Entry",
				filters={"voucher_type": "Sales Invoice", "voucher_no": invoice_name},
				fields=("item_code", "warehouse", "actual_qty", "stock_value_difference"),
				order_by="creation asc",
			)
		]

	def _read_serial_snapshot(self, serial_no):
		if not serial_no:
			return
		if not frappe.db.exists("Serial No", serial_no):
			self._warn("Serial No 無法讀取；已略過 submit 後序號狀態觀察。")
			return
		serial_doc = frappe.get_doc("Serial No", serial_no)
		self.report["serial_status"] = getattr(serial_doc, "status", None)
		self.report["serial_warehouse"] = getattr(serial_doc, "warehouse", None)

	def _journal_totals(self, accounts):
		debit = sum(flt(row.get("debit_in_account_currency") or row.get("debit")) for row in accounts)
		credit = sum(flt(row.get("credit_in_account_currency") or row.get("credit")) for row in accounts)
		return debit, credit

	def _resolve_cash_or_bank_account(self, accounts):
		for row in accounts:
			if flt(row.get("debit_in_account_currency") or row.get("debit")) <= 0:
				continue
			account = row.get("account")
			account_type = frappe.db.get_value("Account", account, "account_type") if account else None
			if account_type in {"Bank", "Cash"}:
				return account
		return None

	def _resolve_advance_account(self, voucher, journal_accounts, credit=False):
		amount_field = "credit" if credit else "debit"
		for row in list(voucher.get("lines") or []) if voucher else []:
			if flt(row.get(amount_field)) > 0 and self._is_advance_account(row.get("account")):
				return row.get("account")
		for row in journal_accounts:
			amount = row.get(f"{amount_field}_in_account_currency") or row.get(amount_field)
			if flt(amount) > 0 and self._is_advance_account(row.get("account")):
				return row.get("account")
		return None

	def _is_advance_account(self, account):
		if not account:
			return False
		root_type = frappe.db.get_value("Account", account, "root_type")
		return root_type == "Liability" or any(keyword in account for keyword in ADVANCE_ACCOUNT_KEYWORDS)

	def _count_optional_target_link(self, doctype, target):
		fieldname = SIDE_EFFECT_LINK_FIELDS.get(doctype)
		if not fieldname or not frappe.get_meta(doctype).has_field(fieldname):
			return 0
		return frappe.db.count(doctype, {fieldname: target})

	def _count_unexpected_journal_entries(self, target):
		allowed = {self.report.get("advance_settlement_journal_entry")}
		count = 0
		for fieldname in ("cheque_no", "reference_name"):
			if not frappe.get_meta("Journal Entry").has_field(fieldname):
				continue
			entries = frappe.db.get_all("Journal Entry", filters={fieldname: target}, fields=("name",))
			count += len([row for row in entries if row.get("name") not in allowed])
		return count

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
		self.report["closed"] = self.report["status"] == "pass"
		self.report["ready_for_ui_review"] = self.report["closed"] is True


def _get_formal_sale_accounting_closure_candidates(limit=10):
	vehicles = frappe.db.get_all(
		"Used Car Vehicle",
		filters={
			"status": "已售出",
			"formal_delivery_status": "已完成",
			"sales_invoice": ["is", "set"],
			"advance_settlement_journal_entry": ["is", "set"],
		},
		fields=("name", "sales_invoice", "advance_settlement_journal_entry", "status", "formal_delivery_status", "completed_reservation", "modified"),
		order_by="modified desc",
		limit=limit,
	)
	results = []
	for vehicle in vehicles:
		invoice_name = vehicle.get("sales_invoice")
		settlement = vehicle.get("advance_settlement_journal_entry")
		if not invoice_name or not settlement:
			continue
		if not frappe.db.exists("Sales Invoice", invoice_name) or not frappe.db.exists("Journal Entry", settlement):
			continue
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		journal_entry = frappe.get_doc("Journal Entry", settlement)
		if int(getattr(invoice, "docstatus", 0) or 0) != 1:
			continue
		if int(journal_entry.get("docstatus") or 0) != 1:
			continue
		results.append(
			{
				"vehicle": vehicle.get("name"),
				"sales_invoice": invoice_name,
				"advance_settlement_journal_entry": settlement,
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
				"completed_reservation": vehicle.get("completed_reservation"),
				"customer": getattr(invoice, "customer", None),
				"company": getattr(invoice, "company", None),
				"sales_invoice_docstatus": getattr(invoice, "docstatus", None),
				"advance_settlement_journal_entry_docstatus": journal_entry.get("docstatus"),
				"grand_total": getattr(invoice, "grand_total", None),
				"outstanding_amount": getattr(invoice, "outstanding_amount", None),
				"modified": vehicle.get("modified"),
			}
		)
	return results


@frappe.whitelist()
def run_formal_sale_accounting_closure_inspector(sales_invoice=None, vehicle_name=None):
	return FormalSaleAccountingClosureInspectorService().run(sales_invoice=sales_invoice, vehicle_name=vehicle_name)


@frappe.whitelist()
def find_formal_sale_accounting_closure_candidates(limit=10):
	return FormalSaleAccountingClosureInspectorService().find_candidates(limit=limit)
