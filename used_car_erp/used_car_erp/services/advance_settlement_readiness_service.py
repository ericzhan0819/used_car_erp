import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service import COMPANY, RECEIVABLE_ACCOUNT


ROUNDING_TOLERANCE = 0.01
ADVANCE_ACCOUNT_KEYWORDS = ("預收", "暫收")

REPORT_KEYS = (
	"status",
	"ready_to_create_advance_settlement",
	"company",
	"vehicle",
	"sales_invoice",
	"reservation",
	"customer",
	"receivable_account",
	"sales_invoice_grand_total",
	"sales_invoice_outstanding_amount",
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
	"settlement_preview",
	"validations",
	"warnings",
	"blocking_errors",
)


class AdvanceSettlementReadinessService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, sales_invoice=None, vehicle_name=None):
		vehicle = self._resolve_target_vehicle(sales_invoice=sales_invoice, vehicle_name=vehicle_name)
		if not vehicle:
			self._block("找不到符合條件的預收款沖轉 readiness target。")
			self._set_status()
			return self.report

		invoice = self._resolve_target_invoice(vehicle, sales_invoice=sales_invoice)
		self._read_vehicle(vehicle)
		self._read_invoice(invoice)
		reservation = self._read_reservation(vehicle)
		self._validate_vehicle_gate(vehicle, invoice, reservation)
		self._validate_sales_invoice_gate(invoice)
		self._validate_flow_bundle(vehicle, reservation, "deposit", "訂金", "訂金收款")
		self._validate_flow_bundle(vehicle, reservation, "final", "尾款", "尾款收款")
		self._validate_settlement_amounts()
		self._build_settlement_preview()
		self._set_status()
		return self.report

	def find_candidates(self, limit=10):
		return _get_advance_settlement_readiness_candidates(limit=limit)

	def _new_report(self):
		return {key: [] if key in {"validations", "warnings", "blocking_errors"} else None for key in REPORT_KEYS} | {
			"status": "fail",
			"ready_to_create_advance_settlement": False,
			"company": COMPANY,
			"sales_invoice_grand_total": 0,
			"sales_invoice_outstanding_amount": 0,
			"deposit_amount": 0,
			"final_amount": 0,
			"advance_total": 0,
			"settlement_preview": [],
		}

	def _resolve_target_vehicle(self, sales_invoice=None, vehicle_name=None):
		if vehicle_name:
			self.report["vehicle"] = vehicle_name
			if not frappe.db.exists("Used Car Vehicle", vehicle_name):
				return None
			return frappe.get_doc("Used Car Vehicle", vehicle_name)

		if sales_invoice:
			self.report["sales_invoice"] = sales_invoice
			vehicle = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": sales_invoice}, "name")
			if vehicle and frappe.db.exists("Used Car Vehicle", vehicle):
				return frappe.get_doc("Used Car Vehicle", vehicle)
			return None

		candidates = self.find_candidates(limit=1)
		if not candidates:
			return None
		vehicle = candidates[0].get("vehicle")
		return frappe.get_doc("Used Car Vehicle", vehicle) if vehicle and frappe.db.exists("Used Car Vehicle", vehicle) else None

	def _resolve_target_invoice(self, vehicle, sales_invoice=None):
		invoice_name = sales_invoice or vehicle.get("sales_invoice")
		self.report["sales_invoice"] = invoice_name
		if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
			return None
		return frappe.get_doc("Sales Invoice", invoice_name)

	def _read_vehicle(self, vehicle):
		self.report.update(
			{
				"vehicle": vehicle.get("name"),
				"reservation": vehicle.get("completed_reservation"),
				"deposit_money_flow": vehicle.get("deposit_money_flow"),
				"deposit_voucher_draft": vehicle.get("deposit_voucher_draft"),
				"deposit_journal_entry": vehicle.get("deposit_journal_entry"),
				"final_money_flow": vehicle.get("final_money_flow"),
				"final_voucher_draft": vehicle.get("final_voucher_draft"),
				"final_journal_entry": vehicle.get("final_journal_entry"),
			}
		)

	def _read_invoice(self, invoice):
		if not invoice:
			return
		self.report.update(
			{
				"company": getattr(invoice, "company", None),
				"customer": getattr(invoice, "customer", None),
				"sales_invoice_grand_total": flt(getattr(invoice, "grand_total", 0)),
				"sales_invoice_outstanding_amount": flt(getattr(invoice, "outstanding_amount", 0)),
			}
		)

	def _read_reservation(self, vehicle):
		reservation_name = vehicle.get("completed_reservation")
		if not reservation_name or not frappe.db.exists("Used Car Reservation", reservation_name):
			return None
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		self.report["reservation"] = reservation.name
		if not self.report.get("customer"):
			self.report["customer"] = reservation.get("customer")
		return reservation

	def _validate_vehicle_gate(self, vehicle, invoice, reservation):
		if vehicle.get("status") != "已售出":
			self._block("Used Car Vehicle status 必須是 已售出。")
		if vehicle.get("formal_delivery_status") != "已完成":
			self._block("Used Car Vehicle formal_delivery_status 必須是 已完成。")
		if invoice and vehicle.get("sales_invoice") != invoice.name:
			self._block("Used Car Vehicle.sales_invoice 必須等於 target Sales Invoice。")
		elif not vehicle.get("sales_invoice"):
			self._block("Used Car Vehicle 缺少 sales_invoice。")
		if vehicle.get("advance_settlement_journal_entry"):
			self._block("Used Car Vehicle 已有 advance_settlement_journal_entry，不可重複沖轉。")
		if not reservation:
			self._block("缺少已完成保留單 completed_reservation。")
		elif reservation.get("status") != "已完成":
			self._block("completed_reservation 狀態必須是 已完成。")

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
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": invoice.name},
			fields=("account", "debit", "credit"),
			order_by="account asc",
		)
		if not gl_entries:
			self._block("找不到 Sales Invoice 對應 GL Entry。")
		self.report["receivable_account"] = self._resolve_receivable_account(invoice, gl_entries)
		if not self.report["receivable_account"]:
			self._block("無法解析 Sales Invoice receivable account。")

	def _resolve_receivable_account(self, invoice, gl_entries):
		if getattr(invoice, "debit_to", None):
			return invoice.debit_to
		for row in gl_entries:
			if row.get("account") == RECEIVABLE_ACCOUNT:
				return RECEIVABLE_ACCOUNT
		if frappe.db.exists("Account", RECEIVABLE_ACCOUNT):
			return RECEIVABLE_ACCOUNT
		return None

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
			self._validate_journal_entry(journal_entry, voucher, label, prefix)

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
		self._validate_common_links(money_flow, reservation, vehicle, f"{label}金流")
		if not money_flow.get("journal_entry"):
			self._block(f"{label}金流缺少 journal_entry。")

	def _validate_voucher_draft(self, voucher, money_flow, reservation, vehicle, label):
		if voucher.get("status") != "已入帳":
			self._block(f"{label}傳票草稿 status 必須是 已入帳。")
		if not voucher.get("journal_entry"):
			self._block(f"{label}傳票草稿缺少 journal_entry。")
		if money_flow and voucher.get("money_flow") != money_flow.name:
			self._block(f"{label}傳票草稿 money_flow 必須對應金流。")
		self._validate_common_links(voucher, reservation, vehicle, f"{label}傳票草稿")
		if not list(voucher.get("lines") or []):
			self._block(f"{label}傳票草稿缺少 lines。")

	def _validate_journal_entry(self, journal_entry, voucher, label, prefix):
		if int(journal_entry.get("docstatus") or 0) != 1:
			self._block(f"{label} Journal Entry docstatus 必須是 1。")
		if journal_entry.get("company") != COMPANY:
			self._block(f"{label} Journal Entry company 必須是 {COMPANY}。")
		accounts = list(journal_entry.get("accounts") or [])
		if not accounts:
			self._block(f"{label} Journal Entry 缺少 accounts。")
			return
		debit = sum(flt(row.get("debit_in_account_currency") or row.get("debit")) for row in accounts)
		credit = sum(flt(row.get("credit_in_account_currency") or row.get("credit")) for row in accounts)
		self.report["validations"].append({f"{prefix}_journal_debit_total": debit, f"{prefix}_journal_credit_total": credit})
		if flt(debit, 2) != flt(credit, 2):
			self._block(f"{label} Journal Entry debit / credit 不平。")
		cash_or_bank = self._resolve_cash_or_bank_account(accounts)
		if not cash_or_bank:
			self._block(f"{label} Journal Entry 無法解析 cash/bank debit account。")
		advance_account = self._resolve_advance_account(voucher, accounts)
		self.report[f"{prefix}_advance_account"] = advance_account
		if not advance_account:
			self._block(f"{label} Journal Entry 無法解析預收 / 暫收 / 負債 account。")

	def _validate_common_links(self, doc, reservation, vehicle, label):
		if reservation and doc.get("reservation") and doc.get("reservation") != reservation.name:
			self._block(f"{label} reservation 必須對應 completed_reservation。")
		if doc.get("vehicle") and doc.get("vehicle") != vehicle.name:
			self._block(f"{label} vehicle 必須對應 Used Car Vehicle。")
		if self.report.get("customer") and doc.get("customer") and doc.get("customer") != self.report["customer"]:
			self._block(f"{label} customer 必須對應 Sales Invoice customer。")

	def _resolve_cash_or_bank_account(self, accounts):
		for row in accounts:
			if flt(row.get("debit_in_account_currency") or row.get("debit")) <= 0:
				continue
			account = row.get("account")
			account_type = frappe.db.get_value("Account", account, "account_type") if account else None
			if account_type in {"Bank", "Cash"}:
				return account
		return None

	def _resolve_advance_account(self, voucher, journal_accounts):
		for row in list(voucher.get("lines") or []):
			if flt(row.get("credit")) > 0 and self._is_advance_account(row.get("account")):
				return row.get("account")
		for row in journal_accounts:
			if flt(row.get("credit_in_account_currency") or row.get("credit")) > 0 and self._is_advance_account(row.get("account")):
				return row.get("account")
		return None

	def _is_advance_account(self, account):
		if not account:
			return False
		root_type = frappe.db.get_value("Account", account, "root_type")
		return root_type == "Liability" or any(keyword in account for keyword in ADVANCE_ACCOUNT_KEYWORDS)

	def _validate_settlement_amounts(self):
		advance_total = flt(self.report.get("deposit_amount")) + flt(self.report.get("final_amount"))
		grand_total = flt(self.report.get("sales_invoice_grand_total"))
		outstanding = flt(self.report.get("sales_invoice_outstanding_amount"))
		self.report["advance_total"] = advance_total
		if advance_total <= 0:
			self._block("advance_total 必須大於 0。")
		if abs(advance_total - grand_total) > ROUNDING_TOLERANCE:
			if advance_total < grand_total:
				self._block("advance_total 小於 Sales Invoice grand_total；本階段只處理全額收清 fixture。")
			else:
				self._block("advance_total 大於 Sales Invoice grand_total。")
		if flt(outstanding, 2) == 0:
			self._warn("Sales Invoice outstanding_amount 已為 0；readiness 只回報，不直接判定可建立沖轉 JE。")
		elif abs(outstanding - grand_total) <= ROUNDING_TOLERANCE:
			self.report["validations"].append("Sales Invoice outstanding_amount 等於 grand_total，符合尚未沖轉預期。")
		else:
			self._warn("Sales Invoice outstanding_amount 不是 0 也不等於 grand_total，需人工確認。")

	def _build_settlement_preview(self):
		if not self.report.get("receivable_account"):
			return
		advance_rows = {}
		for prefix in ("deposit", "final"):
			account = self.report.get(f"{prefix}_advance_account")
			amount = flt(self.report.get(f"{prefix}_amount"))
			if account and amount > 0:
				advance_rows[account] = flt(advance_rows.get(account)) + amount
		preview = [
			{
				"account": account,
				"debit": amount,
				"credit": 0,
				"reference_type": "Sales Invoice",
				"reference_name": self.report.get("sales_invoice"),
				"vehicle": self.report.get("vehicle"),
				"reservation": self.report.get("reservation"),
			}
			for account, amount in sorted(advance_rows.items())
		]
		if preview:
			preview.append(
				{
					"account": self.report.get("receivable_account"),
					"debit": 0,
					"credit": flt(self.report.get("advance_total")),
					"reference_type": "Sales Invoice",
					"reference_name": self.report.get("sales_invoice"),
					"vehicle": self.report.get("vehicle"),
					"reservation": self.report.get("reservation"),
				}
			)
		self.report["settlement_preview"] = preview

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
		self.report["ready_to_create_advance_settlement"] = self.report["status"] == "pass"


def _get_advance_settlement_readiness_candidates(limit=10):
	vehicles = frappe.db.get_all(
		"Used Car Vehicle",
		filters={
			"status": "已售出",
			"formal_delivery_status": "已完成",
			"sales_invoice": ["is", "set"],
			"advance_settlement_journal_entry": ["is", "not set"],
		},
		fields=("name", "sales_invoice", "status", "formal_delivery_status", "completed_reservation", "modified"),
		order_by="modified desc",
		limit=limit,
	)
	results = []
	for vehicle in vehicles:
		invoice_name = vehicle.get("sales_invoice")
		if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
			continue
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		if int(getattr(invoice, "docstatus", 0) or 0) != 1:
			continue
		results.append(
			{
				"vehicle": vehicle.get("name"),
				"sales_invoice": invoice_name,
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
				"completed_reservation": vehicle.get("completed_reservation"),
				"customer": getattr(invoice, "customer", None),
				"company": getattr(invoice, "company", None),
				"docstatus": getattr(invoice, "docstatus", None),
				"grand_total": getattr(invoice, "grand_total", None),
				"outstanding_amount": getattr(invoice, "outstanding_amount", None),
				"modified": vehicle.get("modified"),
			}
		)
	return results


@frappe.whitelist()
def run_advance_settlement_readiness(sales_invoice=None, vehicle_name=None):
	return AdvanceSettlementReadinessService().run(sales_invoice=sales_invoice, vehicle_name=vehicle_name)


@frappe.whitelist()
def find_advance_settlement_readiness_candidates(limit=10):
	return AdvanceSettlementReadinessService().find_candidates(limit=limit)
