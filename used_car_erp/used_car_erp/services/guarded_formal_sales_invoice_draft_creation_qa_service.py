import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service import (
	FormalSalesInvoiceDraftReadinessService,
)
from used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service import (
	SubmittedSalesInvoicePreflightService,
	run_latest_formal_vehicle_sales_invoice_preflight,
)
from used_car_erp.used_car_erp.services.vehicle_reservation_service import (
	SALES_TAX_ACCOUNT,
	SALES_TAX_RATE,
	SALES_TAX_TEMPLATE,
	VehicleReservationService,
)


COUNT_DOCTYPES = (
	"Sales Invoice",
	"GL Entry",
	"Stock Ledger Entry",
	"Payment Entry",
	"Journal Entry",
	"Delivery Note",
	"Stock Entry",
)

REPORT_KEYS = (
	"status",
	"created",
	"ready_for_submit_preflight",
	"vehicle",
	"reservation",
	"sales_invoice",
	"sales_invoice_docstatus",
	"formal_delivery_status",
	"readiness_status",
	"readiness_report",
	"preflight_status",
	"preflight_report",
	"counts_before",
	"counts_after",
	"validations",
	"warnings",
	"blocking_errors",
)


class GuardedFormalSalesInvoiceDraftCreationQAService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, vehicle_name=None, posting_date=None, note=None):
		readiness = FormalSalesInvoiceDraftReadinessService().run(vehicle_name=vehicle_name)
		self.report["readiness_report"] = readiness
		self.report["readiness_status"] = readiness.get("status")
		self.report["vehicle"] = readiness.get("vehicle")
		self.report["reservation"] = readiness.get("reservation")

		if readiness.get("status") != "pass" or readiness.get("ready_to_create_sales_invoice_draft") is not True:
			self._block("readiness 未通過，guarded QA 不建立 Sales Invoice 草稿。")
			self._set_status(blocked=True)
			return self.report

		self.report["counts_before"] = self._read_counts()
		try:
			result = VehicleReservationService().create_sales_invoice_draft_for_vehicle(
				vehicle_name=readiness.get("vehicle"),
				posting_date=posting_date,
				note=note,
			)
		except Exception as exc:
			self._block(f"建立 Sales Invoice 草稿失敗：{exc}")
			self.report["counts_after"] = self._read_counts()
			self._set_status()
			return self.report

		self.report["created"] = True
		self.report["sales_invoice"] = result.get("sales_invoice")
		self.report["reservation"] = result.get("reservation") or self.report.get("reservation")
		self.report["formal_delivery_status"] = result.get("formal_delivery_status")
		self.report["counts_after"] = self._read_counts()
		self._validate_created_sales_invoice()
		self._validate_count_changes()
		self._run_preflight()
		self._set_status()
		return self.report

	def _new_report(self):
		return {key: [] if key in {"validations", "warnings", "blocking_errors"} else None for key in REPORT_KEYS} | {
			"status": "fail",
			"created": False,
			"ready_for_submit_preflight": False,
			"readiness_report": None,
			"preflight_report": None,
			"counts_before": None,
			"counts_after": None,
		}

	def _read_counts(self):
		return {doctype: frappe.db.count(doctype) for doctype in COUNT_DOCTYPES}

	def _validate_created_sales_invoice(self):
		invoice_name = self.report.get("sales_invoice")
		if not invoice_name:
			self._block("runtime 未回傳 Sales Invoice 名稱。")
			return
		if not frappe.db.exists("Sales Invoice", invoice_name):
			self._block(f"建立後找不到 Sales Invoice：{invoice_name}")
			return

		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		self.report["sales_invoice_docstatus"] = getattr(invoice, "docstatus", None)
		if int(getattr(invoice, "docstatus", 0) or 0) != 0:
			self._block("建立後 Sales Invoice docstatus 必須是 0。")
		if int(getattr(invoice, "update_stock", 0) or 0) != 1:
			self._block("建立後 Sales Invoice update_stock 必須是 1。")
		if getattr(invoice, "taxes_and_charges", None) != SALES_TAX_TEMPLATE:
			self._block(f"建立後 Sales Invoice taxes_and_charges 必須是 {SALES_TAX_TEMPLATE}。")
		self._validate_item_rows(invoice)
		self._validate_tax_rows(invoice)
		self.report["validations"].append("已完成 Sales Invoice 草稿建立後欄位檢查。")

	def _validate_item_rows(self, invoice):
		items = list(getattr(invoice, "items", []) or [])
		if len(items) != 1:
			self._block("建立後 Sales Invoice 必須有且只有一筆 item row。")
			return

		row = items[0]
		if not getattr(row, "serial_no", None):
			self._block("建立後 Sales Invoice item row 必須有 serial_no。")
		if not getattr(row, "warehouse", None):
			self._block("建立後 Sales Invoice item row warehouse 不可為空。")
		if not getattr(row, "income_account", None):
			self._block("建立後 Sales Invoice item row income_account 不可為空。")

	def _validate_tax_rows(self, invoice):
		taxes = list(getattr(invoice, "taxes", []) or [])
		if len(taxes) != 1:
			self._block("建立後 Sales Invoice 必須有且只有一筆 tax row。")
			return

		row = taxes[0]
		if getattr(row, "charge_type", None) != "On Net Total":
			self._block("建立後 tax row charge_type 必須是 On Net Total。")
		if getattr(row, "account_head", None) != SALES_TAX_ACCOUNT:
			self._block(f"建立後 tax row account_head 必須是 {SALES_TAX_ACCOUNT}。")
		if flt(getattr(row, "rate", 0)) != SALES_TAX_RATE:
			self._block(f"建立後 tax row rate 必須是 {SALES_TAX_RATE}。")
		if int(getattr(row, "included_in_print_rate", 0) or 0) != 1:
			self._block("建立後 tax row included_in_print_rate 必須是 1。")

	def _validate_count_changes(self):
		before = self.report.get("counts_before") or {}
		after = self.report.get("counts_after") or {}
		for doctype in COUNT_DOCTYPES:
			if doctype == "Sales Invoice":
				if after.get(doctype) != before.get(doctype, 0) + 1:
					self._block("Sales Invoice count 必須增加 1。")
			elif after.get(doctype) != before.get(doctype):
				self._block(f"{doctype} count 不可改變。")
		self.report["validations"].append("已完成建立前後 accounting / stock 文件 counts 檢查。")

	def _run_preflight(self):
		invoice_name = self.report.get("sales_invoice")
		if not invoice_name:
			return
		preflight = SubmittedSalesInvoicePreflightService().run(sales_invoice=invoice_name)
		self.report["preflight_report"] = preflight
		self.report["preflight_status"] = preflight.get("status")
		self.report["ready_for_submit_preflight"] = preflight.get("ready_to_submit")
		if preflight.get("status") != "pass":
			self._block("建立後 submitted Sales Invoice preflight 未通過。")

		latest_preflight = run_latest_formal_vehicle_sales_invoice_preflight()
		if latest_preflight.get("sales_invoice") != invoice_name:
			self._block("latest formal vehicle Sales Invoice preflight 未找到本次建立的草稿。")
		else:
			self.report["validations"].append("latest formal vehicle Sales Invoice preflight 可找到本次建立的草稿。")

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _set_status(self, blocked=False):
		if blocked:
			self.report["status"] = "blocked"
		elif self.report["blocking_errors"]:
			self.report["status"] = "warning" if self.report["created"] else "fail"
		elif self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"


@frappe.whitelist()
def run_guarded_formal_sales_invoice_draft_creation_qa(vehicle_name=None, posting_date=None, note=None):
	return GuardedFormalSalesInvoiceDraftCreationQAService().run(
		vehicle_name=vehicle_name,
		posting_date=posting_date,
		note=note,
	)
