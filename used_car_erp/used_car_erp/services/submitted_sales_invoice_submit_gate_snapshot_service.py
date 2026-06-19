import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service import (
	COMPANY,
	find_formal_vehicle_sales_invoice_preflight_candidates,
	SubmittedSalesInvoicePreflightService,
	TAX_ACCOUNT,
	TAX_TEMPLATE,
)
from used_car_erp.used_car_erp.services.vehicle_reservation_service import SALES_TAX_RATE


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
	"ready_for_submit_test",
	"sales_invoice",
	"company",
	"customer",
	"docstatus",
	"update_stock",
	"posting_date",
	"due_date",
	"vehicle",
	"vehicle_status",
	"formal_delivery_status",
	"item_code",
	"qty",
	"rate",
	"serial_no",
	"warehouse",
	"income_account",
	"expense_account",
	"taxes_and_charges",
	"tax_charge_type",
	"tax_account",
	"tax_rate",
	"tax_included_in_print_rate",
	"counts",
	"preflight_status",
	"preflight_ready_to_submit",
	"target_mode",
	"baseline_mode",
	"preflight_report",
	"validations",
	"warnings",
	"blocking_errors",
)


class SubmittedSalesInvoiceSubmitGateSnapshotService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, sales_invoice=None):
		self.report["counts"] = self._read_counts()
		target = sales_invoice or self._find_latest_formal_draft_sales_invoice()
		if not target:
			self._block("找不到正式車輛流程 Draft Sales Invoice。")
			self._set_status()
			return self.report

		self.report["sales_invoice"] = target
		if not frappe.db.exists("Sales Invoice", target):
			self._block(f"Sales Invoice 不存在：{target}")
			self._set_status()
			return self.report

		invoice = frappe.get_doc("Sales Invoice", target)
		linked_vehicle = self._resolve_linked_vehicle(target)
		self._read_invoice_snapshot(invoice)
		self._read_vehicle_snapshot(linked_vehicle)
		self._validate_invoice_snapshot(invoice, linked_vehicle)
		self._run_preflight(target)
		self._warn_if_clean_site_baseline_is_not_clean()
		self._set_status()
		return self.report

	def _new_report(self):
		return {key: [] if key in {"validations", "warnings", "blocking_errors"} else None for key in REPORT_KEYS} | {
			"status": "fail",
			"ready_for_submit_test": False,
			"company": COMPANY,
			"counts": None,
			"preflight_report": None,
		}

	def _read_counts(self):
		return {
			"Sales Invoice": frappe.db.count("Sales Invoice"),
			"Sales Invoice docstatus=1": frappe.db.count("Sales Invoice", {"docstatus": 1}),
			"GL Entry": frappe.db.count("GL Entry"),
			"Stock Ledger Entry": frappe.db.count("Stock Ledger Entry"),
			"Payment Entry": frappe.db.count("Payment Entry"),
			"Journal Entry": frappe.db.count("Journal Entry"),
			"Delivery Note": frappe.db.count("Delivery Note"),
			"Stock Entry": frappe.db.count("Stock Entry"),
		}

	def _find_latest_formal_draft_sales_invoice(self):
		candidates = find_formal_vehicle_sales_invoice_preflight_candidates(limit=1)
		return candidates[0].get("sales_invoice") if candidates else None

	def _resolve_linked_vehicle(self, invoice_name):
		vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": invoice_name}, "name")
		if not vehicle_name:
			return None
		return frappe.get_doc("Used Car Vehicle", vehicle_name)

	def _read_invoice_snapshot(self, invoice):
		items = list(getattr(invoice, "items", []) or [])
		taxes = list(getattr(invoice, "taxes", []) or [])
		item = items[0] if items else None
		tax = taxes[0] if taxes else None

		self.report.update(
			{
				"company": getattr(invoice, "company", None),
				"customer": getattr(invoice, "customer", None),
				"docstatus": getattr(invoice, "docstatus", None),
				"update_stock": getattr(invoice, "update_stock", None),
				"posting_date": getattr(invoice, "posting_date", None),
				"due_date": getattr(invoice, "due_date", None),
				"item_code": getattr(item, "item_code", None) if item else None,
				"qty": getattr(item, "qty", None) if item else None,
				"rate": getattr(item, "rate", None) if item else None,
				"serial_no": getattr(item, "serial_no", None) if item else None,
				"warehouse": getattr(item, "warehouse", None) if item else None,
				"income_account": getattr(item, "income_account", None) if item else None,
				"expense_account": getattr(item, "expense_account", None) if item else None,
				"taxes_and_charges": getattr(invoice, "taxes_and_charges", None),
				"tax_charge_type": getattr(tax, "charge_type", None) if tax else None,
				"tax_account": getattr(tax, "account_head", None) if tax else None,
				"tax_rate": getattr(tax, "rate", None) if tax else None,
				"tax_included_in_print_rate": getattr(tax, "included_in_print_rate", None) if tax else None,
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
		for fieldname in ("item", "serial_no", "completed_reservation"):
			self.report["validations"].append(f"Used Car Vehicle.{fieldname} = {vehicle.get(fieldname)}")

	def _validate_invoice_snapshot(self, invoice, linked_vehicle):
		if int(getattr(invoice, "docstatus", 0) or 0) != 0:
			self._block("target Sales Invoice 必須是 Draft，docstatus 必須為 0。")
		if not linked_vehicle:
			self._block("target Sales Invoice 沒有 linked Used Car Vehicle。")
		else:
			if linked_vehicle.get("status") != "已售出":
				self._block("linked Used Car Vehicle status 必須是 已售出。")
			if linked_vehicle.get("formal_delivery_status") != "銷售發票草稿":
				self._block("linked Used Car Vehicle formal_delivery_status 必須是 銷售發票草稿。")
		if int(getattr(invoice, "update_stock", 0) or 0) != 1:
			self._block("Sales Invoice update_stock 必須為 1。")
		if not getattr(invoice, "customer", None):
			self._block("Sales Invoice customer 不可為空。")
		self._validate_item_rows(invoice)
		self._validate_tax_rows(invoice)

	def _validate_item_rows(self, invoice):
		items = list(getattr(invoice, "items", []) or [])
		if len(items) != 1:
			self._block("Sales Invoice item row 必須剛好一筆。")
			return
		row = items[0]
		if not getattr(row, "serial_no", None):
			self._block("Sales Invoice item row 缺少 serial_no。")
		if not getattr(row, "warehouse", None):
			self._block("Sales Invoice item row 缺少 warehouse。")
		if not getattr(row, "income_account", None):
			self._block("Sales Invoice item row 缺少 income_account。")

	def _validate_tax_rows(self, invoice):
		if getattr(invoice, "taxes_and_charges", None) != TAX_TEMPLATE:
			self._block(f"Sales Invoice taxes_and_charges 必須是 {TAX_TEMPLATE}。")
		taxes = list(getattr(invoice, "taxes", []) or [])
		if len(taxes) != 1:
			self._block("Sales Invoice tax row 必須剛好一筆。")
			return
		row = taxes[0]
		if getattr(row, "charge_type", None) != "On Net Total":
			self._block("Sales Invoice tax row charge_type 必須是 On Net Total。")
		if getattr(row, "account_head", None) != TAX_ACCOUNT:
			self._block(f"Sales Invoice tax row account_head 必須是 {TAX_ACCOUNT}。")
		if flt(getattr(row, "rate", 0)) != SALES_TAX_RATE:
			self._block(f"Sales Invoice tax row rate 必須是 {SALES_TAX_RATE}。")
		if int(getattr(row, "included_in_print_rate", 0) or 0) != 1:
			self._block("Sales Invoice tax row included_in_print_rate 必須是 1。")

	def _run_preflight(self, invoice_name):
		preflight = SubmittedSalesInvoicePreflightService().run(sales_invoice=invoice_name)
		self.report["preflight_report"] = preflight
		self.report["preflight_status"] = preflight.get("status")
		self.report["preflight_ready_to_submit"] = preflight.get("ready_to_submit")
		self.report["target_mode"] = preflight.get("target_mode")
		self.report["baseline_mode"] = preflight.get("baseline_mode")
		if preflight.get("status") != "pass":
			self._block("SubmittedSalesInvoicePreflightService 回傳 fail / warning，submit gate 不通過。")

	def _warn_if_clean_site_baseline_is_not_clean(self):
		counts = self.report.get("counts") or {}
		if counts.get("Sales Invoice docstatus=1", 0) > 0:
			self._warn("baseline counts 已有 submitted Sales Invoice；clean-site 假設已被破壞，本 snapshot 不修資料。")

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _warn(self, message):
		self.report["warnings"].append(message)

	def _set_status(self):
		if self.report["blocking_errors"] or self.report.get("preflight_status") not in {None, "pass"}:
			self.report["status"] = "fail"
		elif self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"

		self.report["ready_for_submit_test"] = self.report["status"] == "pass" and self.report.get("preflight_ready_to_submit") is True


@frappe.whitelist()
def run_submitted_sales_invoice_submit_gate_snapshot(sales_invoice=None):
	return SubmittedSalesInvoiceSubmitGateSnapshotService().run(sales_invoice=sales_invoice)
