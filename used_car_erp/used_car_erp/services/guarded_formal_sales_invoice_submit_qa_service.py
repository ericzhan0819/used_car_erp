import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service import (
	COMPANY,
	EXPENSE_ACCOUNT,
	INCOME_ACCOUNT,
	INVENTORY_ACCOUNT,
	RECEIVABLE_ACCOUNT,
	TAX_ACCOUNT,
	TAX_TEMPLATE,
)
from used_car_erp.used_car_erp.services.submitted_sales_invoice_submit_gate_snapshot_service import (
	SubmittedSalesInvoiceSubmitGateSnapshotService,
)


EXPECTED_SITE = "erpnext-coa.test"
CONFIRMATION_TOKEN = "P1-ACC-6F-C-SUBMIT"

COUNT_DOCTYPES = (
	"Sales Invoice",
	"Sales Invoice docstatus=1",
	"GL Entry",
	"Stock Ledger Entry",
	"Payment Entry",
	"Journal Entry",
	"Delivery Note",
	"Stock Entry",
)

REPORT_KEYS = (
	"status",
	"submitted",
	"already_submitted",
	"ready_for_post_submit_review",
	"site",
	"sales_invoice",
	"sales_invoice_docstatus_before",
	"sales_invoice_docstatus_after",
	"vehicle",
	"vehicle_status",
	"formal_delivery_status",
	"customer",
	"company",
	"serial_no",
	"serial_status_after",
	"serial_warehouse_after",
	"submit_gate_status",
	"submit_gate_report",
	"counts_before",
	"counts_after",
	"count_deltas",
	"new_gl_entry_count",
	"new_stock_ledger_entry_count",
	"new_gl_accounts",
	"new_stock_ledger_entries",
	"validations",
	"warnings",
	"blocking_errors",
)

UNCHANGED_AFTER_SUBMIT_DOCTYPES = ("Payment Entry", "Journal Entry", "Delivery Note", "Stock Entry")


class GuardedFormalSalesInvoiceSubmitQAService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, sales_invoice=None, confirmation_token=None):
		self.report["site"] = self._site()
		if self.report["site"] != EXPECTED_SITE:
			self._block(f"此 submit QA 只能在 {EXPECTED_SITE} 執行，目前站台是 {self.report['site']}。")
			self._set_status("blocked")
			return self.report

		if confirmation_token != CONFIRMATION_TOKEN:
			self._block("confirmation token 不正確，不提交 Sales Invoice。")
			self._set_status("blocked")
			return self.report

		target = sales_invoice or self._find_default_target()
		self.report["sales_invoice"] = target
		if not target or not frappe.db.exists("Sales Invoice", target):
			self._block(f"Sales Invoice 不存在：{target}")
			self._set_status("blocked")
			return self.report

		invoice = frappe.get_doc("Sales Invoice", target)
		self.report["sales_invoice_docstatus_before"] = int(getattr(invoice, "docstatus", 0) or 0)
		linked_vehicle = self._resolve_linked_vehicle(target)
		self._read_invoice_snapshot(invoice)
		self._read_vehicle_snapshot(linked_vehicle)

		if self._is_already_submitted_same_target(invoice, linked_vehicle):
			self._observe_already_submitted(target, invoice, linked_vehicle)
			return self.report

		self._validate_target_before_submit(invoice, linked_vehicle)
		self.report["counts_before"] = self._read_counts()
		if (self.report["counts_before"] or {}).get("Sales Invoice docstatus=1", 0) > 0:
			self._block("submitted Sales Invoice count 已大於 0，且 target 不是同一張 already-submitted formal fixture。")

		self._run_submit_gate_snapshot(target)
		if self.report["blocking_errors"]:
			self._set_status("blocked")
			return self.report

		try:
			invoice = frappe.get_doc("Sales Invoice", target)
			invoice.submit()
			frappe.db.commit()
		except Exception as exc:
			self._block(f"Sales Invoice submit 失敗：{exc}")
			self.report["counts_after"] = self._read_counts()
			self._set_status("fail")
			return self.report

		self.report["submitted"] = True
		self._read_after_submit(target)
		self._validate_after_submit()
		self._set_status("warning" if self.report["blocking_errors"] else "pass")
		return self.report

	def _new_report(self):
		return {key: [] if key in {"new_gl_accounts", "new_stock_ledger_entries", "validations", "warnings", "blocking_errors"} else None for key in REPORT_KEYS} | {
			"status": "fail",
			"submitted": False,
			"already_submitted": False,
			"ready_for_post_submit_review": False,
			"submit_gate_report": None,
			"counts_before": None,
			"counts_after": None,
			"count_deltas": None,
			"new_gl_entry_count": 0,
			"new_stock_ledger_entry_count": 0,
		}

	def _site(self):
		return getattr(getattr(frappe, "local", None), "site", None)

	def _find_default_target(self):
		return SubmittedSalesInvoiceSubmitGateSnapshotService()._find_latest_formal_draft_sales_invoice()

	def _resolve_linked_vehicle(self, invoice_name):
		vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": invoice_name}, "name")
		if not vehicle_name:
			return None
		return frappe.get_doc("Used Car Vehicle", vehicle_name)

	def _read_counts(self):
		counts = {}
		for doctype in COUNT_DOCTYPES:
			if doctype == "Sales Invoice docstatus=1":
				counts[doctype] = frappe.db.count("Sales Invoice", {"docstatus": 1})
			else:
				counts[doctype] = frappe.db.count(doctype)
		return counts

	def _read_invoice_snapshot(self, invoice):
		items = list(getattr(invoice, "items", []) or [])
		row = items[0] if items else None
		self.report.update(
			{
				"customer": getattr(invoice, "customer", None),
				"company": getattr(invoice, "company", None),
				"serial_no": getattr(row, "serial_no", None) if row else None,
			}
		)

	def _read_vehicle_snapshot(self, vehicle):
		if not vehicle:
			return
		self.report.update(
			{
				"vehicle": getattr(vehicle, "name", None),
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
			}
		)

	def _is_already_submitted_same_target(self, invoice, linked_vehicle):
		if int(getattr(invoice, "docstatus", 0) or 0) != 1:
			return False
		if not linked_vehicle or linked_vehicle.get("sales_invoice") != invoice.name:
			return False
		return frappe.db.count("Sales Invoice", {"docstatus": 1}) == 1

	def _observe_already_submitted(self, target, invoice, linked_vehicle):
		self.report["already_submitted"] = True
		self.report["counts_before"] = self._read_counts()
		self.report["counts_after"] = dict(self.report["counts_before"])
		self.report["sales_invoice_docstatus_after"] = int(getattr(invoice, "docstatus", 0) or 0)
		self._read_after_submit(target, invoice=invoice, vehicle=linked_vehicle, counts_already_read=True)
		self._validate_after_submit()
		self._set_status("already_submitted")

	def _validate_target_before_submit(self, invoice, linked_vehicle):
		if int(getattr(invoice, "docstatus", 0) or 0) != 0:
			self._block("target Sales Invoice 必須是 Draft，docstatus 必須為 0。")
		if not linked_vehicle:
			self._block("target Sales Invoice 沒有 linked Used Car Vehicle。")
			return
		if linked_vehicle.get("sales_invoice") != invoice.name:
			self._block("linked Used Car Vehicle.sales_invoice 必須等於 target。")
		if linked_vehicle.get("status") != "已售出":
			self._block("linked Used Car Vehicle status 必須是 已售出。")
		if linked_vehicle.get("formal_delivery_status") != "銷售發票草稿":
			self._block("linked Used Car Vehicle formal_delivery_status 必須是 銷售發票草稿。")

	def _run_submit_gate_snapshot(self, target):
		snapshot = SubmittedSalesInvoiceSubmitGateSnapshotService().run(sales_invoice=target)
		self.report["submit_gate_report"] = snapshot
		self.report["submit_gate_status"] = snapshot.get("status")
		if snapshot.get("status") != "pass" or snapshot.get("ready_for_submit_test") is not True:
			self._block("submit gate snapshot 未通過，不提交 Sales Invoice。")

	def _read_after_submit(self, target, invoice=None, vehicle=None, counts_already_read=False):
		invoice = invoice or frappe.get_doc("Sales Invoice", target)
		vehicle = vehicle or self._resolve_linked_vehicle(target)
		self.report["sales_invoice_docstatus_after"] = int(getattr(invoice, "docstatus", 0) or 0)
		self._read_invoice_snapshot(invoice)
		self._read_vehicle_snapshot(vehicle)
		if not counts_already_read:
			self.report["counts_after"] = self._read_counts()
		self._record_count_deltas()
		self._read_target_gl_entries(target)
		self._read_target_stock_ledger_entries(target)
		self._read_serial_after()

	def _record_count_deltas(self):
		before = self.report.get("counts_before") or {}
		after = self.report.get("counts_after") or {}
		self.report["count_deltas"] = {doctype: after.get(doctype, 0) - before.get(doctype, 0) for doctype in COUNT_DOCTYPES}

	def _read_target_gl_entries(self, target):
		entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": target},
			fields=("account", "debit", "credit"),
			order_by="account asc",
		)
		accounts = []
		for row in entries:
			accounts.append(
				{
					"account": row.get("account"),
					"debit": flt(row.get("debit")),
					"credit": flt(row.get("credit")),
				}
			)
		self.report["new_gl_accounts"] = accounts
		self.report["new_gl_entry_count"] = len(accounts)

	def _read_target_stock_ledger_entries(self, target):
		entries = frappe.db.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": target},
			fields=("item_code", "warehouse", "actual_qty", "stock_value_difference"),
			order_by="creation asc",
		)
		self.report["new_stock_ledger_entries"] = [
			{
				"item_code": row.get("item_code"),
				"warehouse": row.get("warehouse"),
				"actual_qty": flt(row.get("actual_qty")),
				"stock_value_difference": flt(row.get("stock_value_difference")),
			}
			for row in entries
		]
		self.report["new_stock_ledger_entry_count"] = len(self.report["new_stock_ledger_entries"])

	def _read_serial_after(self):
		serial_no = self.report.get("serial_no")
		if not serial_no or not frappe.db.exists("Serial No", serial_no):
			self._warn("Serial No 狀態欄位無法可靠讀取；已略過 submit 後序號狀態檢查。")
			return
		serial_doc = frappe.get_doc("Serial No", serial_no)
		self.report["serial_status_after"] = getattr(serial_doc, "status", None)
		self.report["serial_warehouse_after"] = getattr(serial_doc, "warehouse", None)

	def _validate_after_submit(self):
		invoice = frappe.get_doc("Sales Invoice", self.report["sales_invoice"])
		items = list(getattr(invoice, "items", []) or [])
		row = items[0] if items else None
		if int(getattr(invoice, "docstatus", 0) or 0) != 1:
			self._block("submit 後 Sales Invoice docstatus 必須為 1。")
		if getattr(invoice, "company", None) != COMPANY:
			self._block(f"Sales Invoice company 必須是 {COMPANY}。")
		if int(getattr(invoice, "update_stock", 0) or 0) != 1:
			self._block("Sales Invoice update_stock 必須為 1。")
		if getattr(invoice, "taxes_and_charges", None) != TAX_TEMPLATE:
			self._block(f"Sales Invoice taxes_and_charges 必須是 {TAX_TEMPLATE}。")
		if len(items) != 1:
			self._block("Sales Invoice item row 必須剛好一筆。")
		elif not all(getattr(row, fieldname, None) for fieldname in ("serial_no", "warehouse", "income_account", "expense_account")):
			self._block("Sales Invoice item row serial_no / warehouse / income_account / expense_account 不可為空。")
		self._validate_counts_after_submit()
		self._validate_gl_entries()
		self._validate_stock_ledger_entries()
		self._validate_vehicle_after_submit()

	def _validate_counts_after_submit(self):
		deltas = self.report.get("count_deltas") or {}
		if self.report["submitted"]:
			if deltas.get("Sales Invoice") != 0:
				self._block("Sales Invoice count submit 前後不可改變。")
			if deltas.get("Sales Invoice docstatus=1") != 1:
				self._block("submitted Sales Invoice count submit 後必須增加 1。")
			if deltas.get("GL Entry", 0) <= 0:
				self._block("GL Entry count submit 後必須增加。")
			if deltas.get("Stock Ledger Entry", 0) <= 0:
				self._block("Stock Ledger Entry count submit 後必須增加。")
		for doctype in UNCHANGED_AFTER_SUBMIT_DOCTYPES:
			if deltas.get(doctype) != 0:
				self._block(f"{doctype} count submit 前後不可改變。")

	def _validate_gl_entries(self):
		entries = self.report.get("new_gl_accounts") or []
		accounts = {row.get("account") for row in entries}
		if not entries:
			self._block("找不到 target Sales Invoice 對應 GL Entry。")
		for account, label in (
			(RECEIVABLE_ACCOUNT, "Receivable"),
			(INCOME_ACCOUNT, "Sales income"),
			(TAX_ACCOUNT, "Sales tax"),
			(INVENTORY_ACCOUNT, "Inventory"),
			(EXPENSE_ACCOUNT, "COGS"),
		):
			if account not in accounts:
				self._block(f"target GL Entry 缺少 {label} account：{account}")
		debit = sum(flt(row.get("debit")) for row in entries)
		credit = sum(flt(row.get("credit")) for row in entries)
		self.report["validations"].append({"gl_debit_total": debit, "gl_credit_total": credit})
		if flt(debit, 2) != flt(credit, 2):
			self._block("target GL Entry debit / credit 不平。")

	def _validate_stock_ledger_entries(self):
		if not self.report.get("new_stock_ledger_entries"):
			self._block("找不到 target Sales Invoice 對應 Stock Ledger Entry。")

	def _validate_vehicle_after_submit(self):
		vehicle = self._resolve_linked_vehicle(self.report["sales_invoice"])
		if not vehicle:
			self._block("submit 後 linked Used Car Vehicle 不存在。")
			return
		if vehicle.get("sales_invoice") != self.report["sales_invoice"]:
			self._block("submit 後 vehicle.sales_invoice 必須仍等於 target。")
		if vehicle.get("status") != "已售出":
			self._block("submit 後 vehicle.status 必須仍是 已售出。")
		if vehicle.get("formal_delivery_status") == "銷售發票草稿":
			self._warn("Sales Invoice 已提交，但 formal_delivery_status 尚未同步為已完成；留待下一階段 formal delivery status sync。")

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _warn(self, message):
		self.report["warnings"].append(message)

	def _set_status(self, status):
		self.report["status"] = status
		self.report["ready_for_post_submit_review"] = (
			(self.report["submitted"] or self.report["already_submitted"]) and not self.report["blocking_errors"]
		)


@frappe.whitelist()
def run_guarded_formal_sales_invoice_submit_qa(sales_invoice=None, confirmation_token=None):
	return GuardedFormalSalesInvoiceSubmitQAService().run(
		sales_invoice=sales_invoice,
		confirmation_token=confirmation_token,
	)
