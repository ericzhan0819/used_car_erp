import frappe
from frappe.utils import flt, now_datetime, nowdate

from used_car_erp.used_car_erp.services.vehicle_cost_service import RESTRICTED_ACCOUNTING_DOCTYPES
from used_car_erp.used_car_erp.services.vehicle_profit_tax_estimate_service import (
	get_vehicle_profit_tax_estimate,
)


RESTRICTED_FINAL_CHECK_DOCTYPES = (*RESTRICTED_ACCOUNTING_DOCTYPES, "Tax Summary")
READY_LABEL = "可進入下一階段人工檢查"
WARNING_LABEL = "有待確認項目"
BLOCKED_LABEL = "資料尚未完整"


def get_sold_vehicle_final_check(vehicle_name: str) -> dict:
	vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
	tax_estimate = get_vehicle_profit_tax_estimate(vehicle.name)
	vehicle.reload()
	cost_summary = _build_cost_summary(vehicle, tax_estimate)
	sales_invoice = _get_sales_invoice_summary(vehicle.sales_invoice)
	checks = [
		_build_completion_check(vehicle),
		_build_deposit_check(vehicle),
		_build_final_payment_check(vehicle),
		_build_stock_link_check(vehicle),
		_build_sales_invoice_check(vehicle, sales_invoice),
		_build_cost_summary_check(cost_summary),
		_build_profit_tax_estimate_check(vehicle, tax_estimate),
		_build_tax_metadata_check(vehicle),
	]
	blocked = any(check["state"] == "blocked" for check in checks if check.get("required"))
	warning = any(check["state"] == "warning" for check in checks)
	status = "blocked" if blocked else "warning" if warning else "ready"

	return {
		"vehicle": vehicle.name,
		"status": status,
		"status_label": {"ready": READY_LABEL, "warning": WARNING_LABEL, "blocked": BLOCKED_LABEL}[status],
		"checks": [_public_check(check) for check in checks],
		"sales_invoice": sales_invoice,
		"cost_summary": cost_summary,
		"tax_estimate": _build_tax_estimate_summary(vehicle, tax_estimate),
	}


@frappe.whitelist()
def get_sold_vehicle_final_check_for_vehicle(vehicle_name):
	return get_sold_vehicle_final_check(vehicle_name)


def verify_vehicle_final_check_service():
	vehicle_name = None
	before_counts = _restricted_doc_counts()

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"VERIFY-FINAL-CHECK-{frappe.generate_hash(length=4)}",
				"vin": f"VERIFY-FINAL-CHECK-{frappe.generate_hash(length=10)}",
				"status": "已售出",
				"completed_reservation": "VERIFY-RESERVATION",
				"completed_at": now_datetime(),
				"deposit_money_flow": "VERIFY-DEPOSIT-FLOW",
				"deposit_voucher_draft": "VERIFY-DEPOSIT-DRAFT",
				"deposit_journal_entry": "VERIFY-DEPOSIT-JE",
				"final_money_flow": "VERIFY-FINAL-FLOW",
				"final_voucher_draft": "VERIFY-FINAL-DRAFT",
				"final_journal_entry": "VERIFY-FINAL-JE",
				"item": "VERIFY-ITEM",
				"serial_no": "VERIFY-SERIAL",
				"stock_warehouse": "VERIFY-WAREHOUSE",
				"purchase_price": 500000,
				"sold_price": 600000,
				"vehicle_tax_mode": "15-1 特殊扣抵",
				"tax_review_status": "已確認",
			}
		).insert(ignore_links=True)
		vehicle_name = vehicle.name

		result = get_sold_vehicle_final_check(vehicle.name)
		after_counts = _restricted_doc_counts()

		if result["status"] != "blocked":
			frappe.throw("Vehicle final check verification should be blocked without Sales Invoice draft.")
		if _find_check(result, "sales_invoice")["state"] != "blocked":
			frappe.throw("Vehicle final check verification Sales Invoice check mismatch.")
		for doctype in RESTRICTED_FINAL_CHECK_DOCTYPES:
			if after_counts[doctype] != before_counts[doctype]:
				frappe.throw(f"Vehicle final check must not create {doctype}.")

		return {**result, "cleaned_up": True}
	finally:
		if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
			frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True, ignore_permissions=True)
		frappe.db.commit()


def _build_completion_check(vehicle):
	return _check(
		"completion",
		"成交狀態",
		vehicle.status == "已售出" and vehicle.completed_reservation and vehicle.completed_at,
		"成交狀態已完成。",
		"尚未完成成交確認。",
	)


def _build_deposit_check(vehicle):
	return _check(
		"deposit",
		"訂金入帳",
		vehicle.deposit_money_flow and vehicle.deposit_voucher_draft and vehicle.deposit_journal_entry,
		"訂金金流、傳票草稿與正式會計傳票已完整。",
		"訂金金流、傳票草稿或正式會計傳票尚未完整。",
	)


def _build_final_payment_check(vehicle):
	return _check(
		"final_payment",
		"尾款入帳",
		vehicle.final_money_flow and vehicle.final_voucher_draft and vehicle.final_journal_entry,
		"尾款金流、傳票草稿與正式會計傳票已完整。",
		"尾款金流、傳票草稿或正式會計傳票尚未完整。",
	)


def _build_stock_link_check(vehicle):
	return _check(
		"stock_link",
		"ERPNext 庫存連結",
		vehicle.item and vehicle.serial_no and vehicle.stock_warehouse,
		"ERPNext Item、Serial No 與 Warehouse 已完整。",
		"ERPNext Item、Serial No 或 Warehouse 尚未完整。",
	)


def _build_sales_invoice_check(vehicle, sales_invoice):
	if not vehicle.sales_invoice:
		return _check("sales_invoice", "Sales Invoice 草稿", False, "", "Sales Invoice 草稿尚未建立。")
	if not sales_invoice:
		return _check("sales_invoice", "Sales Invoice 草稿", False, "", "Sales Invoice 草稿無法讀取，請人工確認。")
	if sales_invoice.get("docstatus") != 0:
		return _check(
			"sales_invoice",
			"Sales Invoice 草稿",
			True,
			"Sales Invoice 已不是草稿，請人工確認。",
			"",
			state="warning",
		)
	return _check("sales_invoice", "Sales Invoice 草稿", True, "Sales Invoice 草稿已建立且仍為草稿。", "")


def _build_cost_summary_check(cost_summary):
	return _check(
		"cost_summary",
		"成本摘要",
		flt(cost_summary.get("purchase_price")) > 0
		and flt(cost_summary.get("total_cost")) >= flt(cost_summary.get("purchase_price")),
		"買入金額與單車成本摘要已完整。",
		"買入金額或單車成本摘要尚未完整。",
	)


def _build_profit_tax_estimate_check(vehicle, tax_estimate):
	if flt(vehicle.sold_price) <= 0 or tax_estimate.get("tax_estimate_status") == "資料不足":
		return _check(
			"profit_tax_estimate",
			"損益與營業稅估算",
			False,
			"",
			"成交價或損益與營業稅估算資料尚未完整。",
		)
	if tax_estimate.get("tax_estimate_status") == "需確認":
		return _check(
			"profit_tax_estimate",
			"損益與營業稅估算",
			True,
			"稅務模式尚未確認，預估可扣抵稅額暫列 0。",
			"",
			state="warning",
		)
	return _check("profit_tax_estimate", "損益與營業稅估算", True, "損益與預估營業稅資料已可供人工檢查。", "")


def _build_tax_metadata_check(vehicle):
	valid_review_statuses = {"已初步判斷", "已確認", "已調整", "已鎖定"}
	if vehicle.tax_review_status in {"待補資料", "待確認"}:
		return _check(
			"tax_metadata",
			"稅務資料",
			True,
			"稅務資料尚未完整確認；正式申報前仍需確認。",
			"",
			state="warning",
			required=False,
		)
	return _check(
		"tax_metadata",
		"稅務資料",
		vehicle.vehicle_tax_mode and vehicle.vehicle_tax_mode != "待確認" and vehicle.tax_review_status in valid_review_statuses,
		"稅務資料已具備初步人工檢查基礎。",
		"稅務資料尚未完整確認；正式申報前仍需確認。",
		required=False,
	)


def _check(key, label, ok, ok_message, blocked_message, state=None, required=True):
	return {
		"key": key,
		"label": label,
		"state": state or ("ok" if ok else "blocked"),
		"message": ok_message if ok else blocked_message,
		"required": required,
	}


def _public_check(check):
	return {"key": check["key"], "label": check["label"], "state": check["state"], "message": check["message"]}


def _get_sales_invoice_summary(sales_invoice_name):
	if not sales_invoice_name or not frappe.db.exists("Sales Invoice", sales_invoice_name):
		return None
	invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
	return {
		"name": invoice.name,
		"docstatus": invoice.docstatus,
		"customer": invoice.customer,
		"company": invoice.company,
		"posting_date": invoice.posting_date,
		"grand_total": flt(invoice.grand_total),
		"outstanding_amount": flt(invoice.outstanding_amount),
		"update_stock": invoice.update_stock,
	}


def _build_cost_summary(vehicle, tax_estimate):
	return {
		"purchase_price": flt(tax_estimate.get("purchase_price") or vehicle.purchase_price),
		"capitalized_cost_total": flt(tax_estimate.get("capitalized_cost_total")),
		"total_cost": flt(tax_estimate.get("total_cost") or vehicle.total_cost),
		"sold_price": flt(vehicle.sold_price),
		"gross_margin": flt(tax_estimate.get("gross_margin") or vehicle.gross_margin),
	}


def _build_tax_estimate_summary(vehicle, tax_estimate):
	return {
		"vehicle_tax_mode": tax_estimate.get("vehicle_tax_mode") or vehicle.vehicle_tax_mode,
		"tax_review_status": tax_estimate.get("tax_review_status") or vehicle.tax_review_status,
		"estimated_output_vat": flt(tax_estimate.get("estimated_output_vat")),
		"estimated_input_credit": flt(tax_estimate.get("estimated_input_credit")),
		"estimated_vat_payable": flt(tax_estimate.get("estimated_vat_payable")),
		"estimated_margin_after_vat": flt(tax_estimate.get("estimated_margin_after_vat")),
		"tax_estimate_status": tax_estimate.get("tax_estimate_status"),
		"tax_estimate_note": tax_estimate.get("tax_estimate_note"),
	}


def _find_check(result, key):
	return next(check for check in result["checks"] if check["key"] == key)


def _restricted_doc_counts():
	counts = {}
	for doctype in RESTRICTED_FINAL_CHECK_DOCTYPES:
		counts[doctype] = frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
	return counts
