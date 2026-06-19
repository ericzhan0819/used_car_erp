import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.formal_sale_accounting_closure_inspector_service import (
	FormalSaleAccountingClosureInspectorService,
)


ROUNDING_TOLERANCE = 0.01

REPORT_KEYS = (
	"status",
	"business_status",
	"closed",
	"ready_for_vehicle_page",
	"vehicle",
	"vehicle_status",
	"formal_delivery_status",
	"sales_invoice",
	"sales_invoice_docstatus",
	"sales_invoice_outstanding_amount",
	"advance_settlement_journal_entry",
	"advance_settlement_journal_entry_docstatus",
	"completed_reservation",
	"deposit_money_flow",
	"deposit_money_flow_status",
	"deposit_voucher_draft",
	"deposit_voucher_draft_status",
	"deposit_journal_entry",
	"deposit_journal_entry_docstatus",
	"final_money_flow",
	"final_money_flow_status",
	"final_voucher_draft",
	"final_voucher_draft_status",
	"final_journal_entry",
	"final_journal_entry_docstatus",
	"next_action_code",
	"next_action_label",
	"next_action_area",
	"closure_status",
	"closure_report",
	"summary_cards",
	"validations",
	"warnings",
	"blocking_errors",
)

ACCOUNTING_ERROR_KEYWORDS = (
	"GL Entry",
	"Stock Ledger Entry",
	"docstatus 必須是 1",
	"outstanding_amount 必須為 0",
	"debit / credit 不平",
	"company 必須是",
	"Sales Invoice company",
	"Advance Settlement Journal Entry company",
	"找不到 Sales Invoice 對應",
	"找不到 Advance Settlement Journal Entry 對應",
)


class VehicleAccountingStatusSummaryService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, vehicle_name=None, sales_invoice=None):
		vehicle = self._resolve_target_vehicle(vehicle_name=vehicle_name, sales_invoice=sales_invoice)
		if not vehicle:
			self._block("找不到符合條件的車輛會計狀態摘要 target。")
			self._set_status()
			return self.report

		invoice = self._resolve_invoice(vehicle, sales_invoice=sales_invoice)
		settlement = self._resolve_settlement(vehicle)
		self._read_vehicle(vehicle)
		self._read_invoice(invoice)
		self._read_settlement(settlement)
		self._read_flow_bundle(vehicle, "deposit")
		self._read_flow_bundle(vehicle, "final")
		self._validate_business_data(vehicle, invoice, settlement)
		self._run_closure_inspector_if_relevant(vehicle, invoice, settlement)
		self._decide_business_status(vehicle, invoice, settlement)
		self._build_summary_cards()
		self._set_status()
		return self.report

	def find_candidates(self, limit=10):
		return _get_vehicle_accounting_status_summary_candidates(limit=limit)

	def _new_report(self):
		list_keys = {"summary_cards", "validations", "warnings", "blocking_errors"}
		return {key: [] if key in list_keys else None for key in REPORT_KEYS} | {
			"status": "fail",
			"closed": False,
			"ready_for_vehicle_page": False,
			"sales_invoice_outstanding_amount": 0,
		}

	def _resolve_target_vehicle(self, vehicle_name=None, sales_invoice=None):
		if vehicle_name:
			self.report["vehicle"] = vehicle_name
			return frappe.get_doc("Used Car Vehicle", vehicle_name) if frappe.db.exists("Used Car Vehicle", vehicle_name) else None
		if sales_invoice:
			self.report["sales_invoice"] = sales_invoice
			vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": sales_invoice}, "name")
			return frappe.get_doc("Used Car Vehicle", vehicle_name) if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name) else None
		candidates = self.find_candidates(limit=1)
		vehicle_name = candidates[0].get("vehicle") if candidates else None
		return frappe.get_doc("Used Car Vehicle", vehicle_name) if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name) else None

	def _resolve_invoice(self, vehicle, sales_invoice=None):
		invoice_name = sales_invoice or vehicle.get("sales_invoice")
		self.report["sales_invoice"] = invoice_name
		if not invoice_name:
			return None
		if not frappe.db.exists("Sales Invoice", invoice_name):
			self._block(f"Vehicle linked Sales Invoice 不存在：{invoice_name}")
			return None
		return frappe.get_doc("Sales Invoice", invoice_name)

	def _resolve_settlement(self, vehicle):
		journal_entry = vehicle.get("advance_settlement_journal_entry")
		self.report["advance_settlement_journal_entry"] = journal_entry
		if not journal_entry:
			return None
		if not frappe.db.exists("Journal Entry", journal_entry):
			self._block(f"Vehicle linked advance settlement Journal Entry 不存在：{journal_entry}")
			return None
		return frappe.get_doc("Journal Entry", journal_entry)

	def _read_vehicle(self, vehicle):
		self.report.update(
			{
				"vehicle": vehicle.get("name"),
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
				"completed_reservation": vehicle.get("completed_reservation"),
				"deposit_money_flow": vehicle.get("deposit_money_flow"),
				"deposit_voucher_draft": vehicle.get("deposit_voucher_draft"),
				"deposit_journal_entry": vehicle.get("deposit_journal_entry"),
				"final_money_flow": vehicle.get("final_money_flow"),
				"final_voucher_draft": vehicle.get("final_voucher_draft"),
				"final_journal_entry": vehicle.get("final_journal_entry"),
				"advance_settlement_journal_entry": vehicle.get("advance_settlement_journal_entry"),
			}
		)

	def _read_invoice(self, invoice):
		if not invoice:
			return
		self.report.update(
			{
				"sales_invoice_docstatus": int(getattr(invoice, "docstatus", 0) or 0),
				"sales_invoice_outstanding_amount": flt(getattr(invoice, "outstanding_amount", 0)),
			}
		)

	def _read_settlement(self, settlement):
		if settlement:
			self.report["advance_settlement_journal_entry_docstatus"] = int(settlement.get("docstatus") or 0)

	def _read_flow_bundle(self, vehicle, prefix):
		for doctype, fieldname, status_key, docstatus_key in (
			("Used Car Money Flow", f"{prefix}_money_flow", f"{prefix}_money_flow_status", None),
			("Used Car Voucher Draft", f"{prefix}_voucher_draft", f"{prefix}_voucher_draft_status", None),
			("Journal Entry", f"{prefix}_journal_entry", None, f"{prefix}_journal_entry_docstatus"),
		):
			name = vehicle.get(fieldname)
			if not name:
				continue
			if not frappe.db.exists(doctype, name):
				self._warn(f"{doctype} 連結不存在：{name}")
				continue
			doc = frappe.get_doc(doctype, name)
			if status_key:
				self.report[status_key] = doc.get("status")
			if docstatus_key:
				self.report[docstatus_key] = int(doc.get("docstatus") or 0)

	def _validate_business_data(self, vehicle, invoice, settlement):
		if invoice and vehicle.get("sales_invoice") and vehicle.get("sales_invoice") != invoice.name:
			self._block("Sales Invoice linked vehicle mismatch。")
		if invoice and int(getattr(invoice, "docstatus", 0) or 0) == 2:
			self._block("Sales Invoice 已取消。")
		if settlement and int(settlement.get("docstatus") or 0) == 2:
			self._block("Advance settlement Journal Entry 已取消。")
		if vehicle.get("status") == "已售出" and not self._vehicle_customer(vehicle, invoice):
			self._warn("已售出車輛缺少 customer。")
		if vehicle.get("status") == "已售出" and not vehicle.get("completed_reservation"):
			self._warn("已售出車輛缺少 completed_reservation。")
		self._validate_customer_consistency(vehicle, invoice)

	def _vehicle_customer(self, vehicle, invoice):
		return vehicle.get("customer") or getattr(invoice, "customer", None)

	def _validate_customer_consistency(self, vehicle, invoice):
		customer = self._vehicle_customer(vehicle, invoice)
		reservation = self._get_optional_doc("Used Car Reservation", vehicle.get("completed_reservation"))
		if reservation and customer and reservation.get("customer") and reservation.get("customer") != customer:
			self._warn("completed_reservation customer 與車輛 / Sales Invoice customer 不一致。")
		for doctype, fieldname, label in (
			("Used Car Money Flow", "deposit_money_flow", "訂金金流"),
			("Used Car Money Flow", "final_money_flow", "尾款金流"),
			("Used Car Voucher Draft", "deposit_voucher_draft", "訂金傳票草稿"),
			("Used Car Voucher Draft", "final_voucher_draft", "尾款傳票草稿"),
		):
			doc = self._get_optional_doc(doctype, vehicle.get(fieldname))
			if doc and customer and doc.get("customer") and doc.get("customer") != customer:
				self._warn(f"{label} customer 與車輛 / Sales Invoice customer 不一致。")

	def _get_optional_doc(self, doctype, name):
		if not name or not frappe.db.exists(doctype, name):
			return None
		return frappe.get_doc(doctype, name)

	def _run_closure_inspector_if_relevant(self, vehicle, invoice, settlement):
		if not invoice or not settlement:
			return
		closure = FormalSaleAccountingClosureInspectorService().run(vehicle_name=vehicle.name, sales_invoice=invoice.name)
		self.report["closure_report"] = closure
		self.report["closure_status"] = closure.get("status")

	def _decide_business_status(self, vehicle, invoice, settlement):
		if self._has_missing_link_error() or self._is_cancelled_error():
			return self._set_business("錯誤需處理", "review_accounting_error", "檢查會計異常", "會計作業")
		if self._needs_missing_business_data(vehicle):
			return self._set_business("需補資料", "complete_missing_business_data", "補齊售車資料", "車輛")
		if self._closure_passed(vehicle, invoice, settlement):
			return self._set_business("會計閉環完成", None, "無下一步", None, closed=True)
		if settlement and int(settlement.get("docstatus") or 0) == 1:
			if self._closure_has_accounting_error():
				return self._set_business("錯誤需處理", "review_accounting_error", "檢查會計異常", "會計作業")
			return self._set_business("預收款已沖轉", "review_accounting_closure", "檢查會計閉環", "會計作業")
		if invoice and int(getattr(invoice, "docstatus", 0) or 0) == 1:
			if self.report.get("formal_delivery_status") != "已完成":
				return self._set_business("發票已提交", "sync_formal_delivery_status", "同步正式交車狀態", "會計作業")
			return self._set_business("發票已提交", "create_advance_settlement", "建立預收款沖轉", "會計作業")
		if invoice and int(getattr(invoice, "docstatus", 0) or 0) == 0:
			return self._set_business("已建立發票草稿", "submit_sales_invoice", "提交售車發票", "會計作業")
		if self._needs_accounting_review(vehicle):
			return self._set_business("待會計確認", "review_voucher_drafts", "確認金流入帳", "會計作業")
		return self._set_business("未開始", "start_sale_flow", "建立保留或售車流程", "車輛")

	def _has_missing_link_error(self):
		return any("不存在" in error for error in self.report["blocking_errors"])

	def _is_cancelled_error(self):
		return any("已取消" in error for error in self.report["blocking_errors"])

	def _needs_missing_business_data(self, vehicle):
		if vehicle.get("status") != "已售出":
			return False
		if not self._vehicle_customer(vehicle, None) and not self.report.get("sales_invoice"):
			return True
		if not vehicle.get("completed_reservation"):
			return True
		return any("不一致" in warning for warning in self.report["warnings"])

	def _closure_passed(self, vehicle, invoice, settlement):
		closure = self.report.get("closure_report") or {}
		return (
			vehicle.get("status") == "已售出"
			and vehicle.get("formal_delivery_status") == "已完成"
			and invoice
			and int(getattr(invoice, "docstatus", 0) or 0) == 1
			and settlement
			and int(settlement.get("docstatus") or 0) == 1
			and abs(flt(getattr(invoice, "outstanding_amount", 0))) <= ROUNDING_TOLERANCE
			and closure.get("status") == "pass"
			and closure.get("closed") is True
		)

	def _closure_has_accounting_error(self):
		closure = self.report.get("closure_report") or {}
		errors = list(closure.get("blocking_errors") or [])
		return any(any(keyword in error for keyword in ACCOUNTING_ERROR_KEYWORDS) for error in errors)

	def _needs_accounting_review(self, vehicle):
		if vehicle.get("status") == "保留中" or vehicle.get("completed_reservation"):
			return True
		for prefix in ("deposit", "final"):
			if vehicle.get(f"{prefix}_money_flow") or vehicle.get(f"{prefix}_voucher_draft"):
				if self.report.get(f"{prefix}_money_flow_status") != "已入帳":
					return True
				if self.report.get(f"{prefix}_voucher_draft_status") != "已入帳":
					return True
				if not vehicle.get(f"{prefix}_journal_entry"):
					return True
		return False

	def _set_business(self, business_status, next_action_code, next_action_label, next_action_area, closed=False):
		self.report.update(
			{
				"business_status": business_status,
				"next_action_code": next_action_code,
				"next_action_label": next_action_label,
				"next_action_area": next_action_area,
				"closed": closed,
			}
		)

	def _build_summary_cards(self):
		invoice_status = "未建立"
		if self.report.get("sales_invoice_docstatus") == 0:
			invoice_status = "草稿"
		elif self.report.get("sales_invoice_docstatus") == 1:
			invoice_status = "已提交"
		elif self.report.get("sales_invoice_docstatus") == 2:
			invoice_status = "已取消"

		settlement_status = "未建立"
		if self.report.get("advance_settlement_journal_entry_docstatus") == 0:
			settlement_status = "草稿"
		elif self.report.get("advance_settlement_journal_entry_docstatus") == 1:
			settlement_status = "已完成"
		elif self.report.get("advance_settlement_journal_entry_docstatus") == 2:
			settlement_status = "已取消"

		closure_status = "已完成" if self.report.get("closed") else "未完成"
		self.report["summary_cards"] = [
			{"label": "售車發票", "status": invoice_status, "doctype": "Sales Invoice", "name": self.report.get("sales_invoice")},
			{
				"label": "預收款沖轉",
				"status": settlement_status,
				"doctype": "Journal Entry",
				"name": self.report.get("advance_settlement_journal_entry"),
			},
			{"label": "會計閉環", "status": closure_status, "doctype": None, "name": None},
		]

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _warn(self, message):
		self.report["warnings"].append(message)

	def _set_status(self):
		self.report["closed"] = self.report.get("business_status") == "會計閉環完成"
		self.report["ready_for_vehicle_page"] = bool(self.report.get("vehicle") and self.report.get("business_status"))
		if not self.report["ready_for_vehicle_page"]:
			self.report["status"] = "fail"
		elif self.report.get("business_status") == "錯誤需處理":
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"


def _get_vehicle_accounting_status_summary_candidates(limit=10):
	vehicles = frappe.db.get_all(
		"Used Car Vehicle",
		filters={"status": ["in", ["已售出", "保留中", "庫存中"]]},
		fields=("name", "sales_invoice", "advance_settlement_journal_entry", "status", "formal_delivery_status", "completed_reservation", "modified"),
		order_by="modified desc",
		limit=limit,
	)
	results = []
	for vehicle in vehicles:
		invoice_name = vehicle.get("sales_invoice")
		if invoice_name and not frappe.db.exists("Sales Invoice", invoice_name):
			continue
		if invoice_name and _is_qa_sales_invoice(invoice_name):
			continue
		results.append(
			{
				"vehicle": vehicle.get("name"),
				"sales_invoice": invoice_name,
				"advance_settlement_journal_entry": vehicle.get("advance_settlement_journal_entry"),
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
				"completed_reservation": vehicle.get("completed_reservation"),
				"modified": vehicle.get("modified"),
			}
		)
	return results


def _is_qa_sales_invoice(invoice_name):
	if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
		return False
	invoice = frappe.get_doc("Sales Invoice", invoice_name)
	text = "\n".join(str(getattr(invoice, fieldname, "") or "") for fieldname in ("remarks", "user_remark", "title"))
	return "P1-ACC-6E" in text or "QA" in text


@frappe.whitelist()
def run_vehicle_accounting_status_summary(vehicle_name=None, sales_invoice=None):
	return VehicleAccountingStatusSummaryService().run(vehicle_name=vehicle_name, sales_invoice=sales_invoice)


@frappe.whitelist()
def find_vehicle_accounting_status_summary_candidates(limit=10):
	return VehicleAccountingStatusSummaryService().find_candidates(limit=limit)
