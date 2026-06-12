import frappe
from frappe.utils import flt, nowdate

from used_car_erp.used_car_erp.services.vehicle_cost_service import (
	RESTRICTED_ACCOUNTING_DOCTYPES,
	recalculate_vehicle_cost_summary,
)


VAT_RATE = 0.05


def get_vehicle_profit_tax_estimate(vehicle_name: str) -> dict:
	cost_summary = recalculate_vehicle_cost_summary(vehicle_name)
	vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
	purchase_price = flt(vehicle.purchase_price)
	sale_price_tax_inclusive = flt(vehicle.sold_price)
	capitalized_cost_total = flt(cost_summary.get("capitalized_cost_total"))
	total_cost = flt(cost_summary.get("total_cost"))
	gross_margin = flt(cost_summary.get("gross_margin"))
	vehicle_tax_mode = vehicle.vehicle_tax_mode or "待確認"
	tax_review_status = vehicle.tax_review_status or "待確認"
	deductible_cost_total = _sum_cost_by_tax_deductibility(vehicle.name, "可扣抵")
	nondeductible_cost_total = _sum_cost_by_tax_deductibility(vehicle.name, "不可扣抵")
	pending_cost_total = _sum_cost_by_tax_deductibility(vehicle.name, "待確認")
	estimated_output_vat = _included_vat(sale_price_tax_inclusive) if sale_price_tax_inclusive > 0 else 0
	estimated_15_1_input_credit_raw = 0
	estimated_15_1_input_credit = 0
	estimated_general_input_credit = 0
	estimated_input_credit = 0
	tax_estimate_status = "可估算" if sale_price_tax_inclusive > 0 else "資料不足"
	tax_estimate_note = "此摘要只作管理估算，不是正式申報或會計入帳。"

	if vehicle_tax_mode == "15-1 特殊扣抵":
		estimated_15_1_input_credit_raw = _included_vat(purchase_price)
		estimated_15_1_input_credit = min(estimated_15_1_input_credit_raw, estimated_output_vat)
		estimated_input_credit = estimated_15_1_input_credit
		if sale_price_tax_inclusive <= 0:
			tax_estimate_note = "成交價尚未填寫，預估銷項稅、應納營業稅與扣稅後管理毛利資料不足。"
	elif vehicle_tax_mode == "一般發票扣抵":
		estimated_purchase_input_vat = _included_vat(purchase_price)
		estimated_cost_input_vat = _included_vat(deductible_cost_total)
		estimated_general_input_credit = estimated_purchase_input_vat + estimated_cost_input_vat
		estimated_input_credit = estimated_general_input_credit
		if sale_price_tax_inclusive <= 0:
			tax_estimate_note = "成交價尚未填寫，預估銷項稅、應納營業稅與扣稅後管理毛利資料不足。"
	else:
		# 稅務模式未確認時不得樂觀估列進項扣抵，避免管理數字被誤認為正式可申報稅額。
		tax_estimate_status = "需確認"
		tax_estimate_note = "稅務模式尚未確認，預估可扣抵稅額暫列 0。此摘要只作管理估算，不是正式申報或會計入帳。"

	estimated_vat_payable = max(estimated_output_vat - estimated_input_credit, 0)
	estimated_margin_after_vat = gross_margin - estimated_vat_payable

	return {
		"vehicle": vehicle.name,
		"sale_price_tax_inclusive": sale_price_tax_inclusive,
		"purchase_price": purchase_price,
		"capitalized_cost_total": capitalized_cost_total,
		"deductible_cost_total": deductible_cost_total,
		"nondeductible_cost_total": nondeductible_cost_total,
		"pending_cost_total": pending_cost_total,
		"total_cost": total_cost,
		"gross_margin": gross_margin,
		"vehicle_tax_mode": vehicle_tax_mode,
		"tax_review_status": tax_review_status,
		"purchase_source_type": vehicle.purchase_source_type,
		"purchase_document_type": vehicle.purchase_document_type,
		"purchase_document_no": vehicle.purchase_document_no,
		"estimated_output_vat": estimated_output_vat,
		"estimated_15_1_input_credit_raw": estimated_15_1_input_credit_raw,
		"estimated_15_1_input_credit": estimated_15_1_input_credit,
		"estimated_general_input_credit": estimated_general_input_credit,
		"estimated_input_credit": estimated_input_credit,
		"estimated_vat_payable": estimated_vat_payable,
		"estimated_margin_after_vat": estimated_margin_after_vat,
		"tax_estimate_status": tax_estimate_status,
		"tax_estimate_note": tax_estimate_note,
	}


@frappe.whitelist()
def get_vehicle_profit_tax_estimate_for_vehicle(vehicle_name):
	return get_vehicle_profit_tax_estimate(vehicle_name)


def verify_vehicle_profit_tax_estimate_service():
	vehicle_name = None
	cost_names = []
	before_counts = _restricted_doc_counts()

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"VERIFY-PROFIT-TAX-{frappe.generate_hash(length=4)}",
				"vin": f"VERIFY-PROFIT-TAX-{frappe.generate_hash(length=10)}",
				"purchase_price": 500000,
				"sold_price": 600000,
				"vehicle_tax_mode": "15-1 特殊扣抵",
			}
		).insert()
		vehicle_name = vehicle.name

		capitalized_cost = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle Cost",
				"vehicle": vehicle.name,
				"cost_date": nowdate(),
				"cost_category": "維修",
				"amount": 20000,
				"capitalization_mode": "單車成本",
				"tax_deductibility": "待確認",
			}
		).insert()
		cost_names.append(capitalized_cost.name)

		result = get_vehicle_profit_tax_estimate(vehicle.name)
		after_counts = _restricted_doc_counts()
		expected_output_vat = round(600000 * 5 / 105)
		expected_input_credit = min(round(500000 * 5 / 105), expected_output_vat)

		if flt(result["total_cost"]) != 520000:
			frappe.throw("Vehicle profit tax estimate verification total_cost mismatch.")
		if flt(result["gross_margin"]) != 80000:
			frappe.throw("Vehicle profit tax estimate verification gross_margin mismatch.")
		if result["estimated_output_vat"] != expected_output_vat:
			frappe.throw("Vehicle profit tax estimate verification output VAT mismatch.")
		if result["estimated_15_1_input_credit"] != expected_input_credit:
			frappe.throw("Vehicle profit tax estimate verification 15-1 input credit mismatch.")
		if result["estimated_vat_payable"] != expected_output_vat - expected_input_credit:
			frappe.throw("Vehicle profit tax estimate verification VAT payable mismatch.")
		for doctype in RESTRICTED_ACCOUNTING_DOCTYPES:
			if after_counts[doctype] != before_counts[doctype]:
				frappe.throw(f"Vehicle profit tax estimate must not create {doctype}.")

		return {**result, "cleaned_up": True}
	finally:
		for cost_name in reversed(cost_names):
			if frappe.db.exists("Used Car Vehicle Cost", cost_name):
				frappe.delete_doc("Used Car Vehicle Cost", cost_name, force=True)
		if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
			frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True)
		frappe.db.commit()


def _included_vat(amount):
	return round(flt(amount) * VAT_RATE / (1 + VAT_RATE))


def _sum_cost_by_tax_deductibility(vehicle_name, tax_deductibility):
	return flt(
		frappe.db.get_value(
			"Used Car Vehicle Cost",
			{"vehicle": vehicle_name, "tax_deductibility": tax_deductibility},
			"sum(amount)",
		)
	)


def _restricted_doc_counts():
	return {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
