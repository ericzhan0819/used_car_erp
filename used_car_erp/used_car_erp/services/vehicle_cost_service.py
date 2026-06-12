import frappe
from frappe.utils import flt, nowdate


RESTRICTED_ACCOUNTING_DOCTYPES = (
	"Sales Invoice",
	"Payment Entry",
	"Delivery Note",
	"Stock Entry",
	"Journal Entry",
)


def recalculate_vehicle_cost_summary(vehicle_name: str) -> dict:
	vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
	purchase_price = flt(vehicle.purchase_price)
	capitalized_cost_total = flt(
		frappe.db.get_value(
			"Used Car Vehicle Cost",
			{"vehicle": vehicle.name, "capitalization_mode": "單車成本"},
			"sum(amount)",
		)
	)
	total_cost = purchase_price + capitalized_cost_total
	sold_price = flt(vehicle.sold_price)
	gross_margin = sold_price - total_cost if sold_price > 0 else 0

	# 此處只回寫管理估算欄位，不建立 COGS、庫存異動或正式會計分錄，避免誤作正式入帳結果。
	frappe.db.set_value(
		"Used Car Vehicle",
		vehicle.name,
		{"total_cost": total_cost, "gross_margin": gross_margin},
		update_modified=False,
	)

	return {
		"vehicle": vehicle.name,
		"purchase_price": purchase_price,
		"capitalized_cost_total": capitalized_cost_total,
		"total_cost": total_cost,
		"sold_price": sold_price,
		"gross_margin": gross_margin,
	}


@frappe.whitelist()
def recalculate_vehicle_cost_summary_for_vehicle(vehicle_name):
	return recalculate_vehicle_cost_summary(vehicle_name)


def verify_vehicle_cost_summary_service():
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
				"license_plate": f"VERIFY-COST-{frappe.generate_hash(length=4)}",
				"vin": f"VERIFY-COST-{frappe.generate_hash(length=10)}",
				"purchase_price": 500000,
				"sold_price": 600000,
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
			}
		).insert()
		cost_names.append(capitalized_cost.name)

		excluded_cost = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle Cost",
				"vehicle": vehicle.name,
				"cost_date": nowdate(),
				"cost_category": "其他",
				"amount": 10000,
				"capitalization_mode": "一般營業費用",
			}
		).insert()
		cost_names.append(excluded_cost.name)

		result = recalculate_vehicle_cost_summary(vehicle.name)
		after_counts = _restricted_doc_counts()

		if flt(result["total_cost"]) != 520000:
			frappe.throw("Vehicle cost summary verification total_cost mismatch.")
		if flt(result["gross_margin"]) != 80000:
			frappe.throw("Vehicle cost summary verification gross_margin mismatch.")
		for doctype in RESTRICTED_ACCOUNTING_DOCTYPES:
			if after_counts[doctype] != before_counts[doctype]:
				frappe.throw(f"Vehicle cost summary must not create {doctype}.")

		return {**result, "cleaned_up": True}
	finally:
		for cost_name in reversed(cost_names):
			if frappe.db.exists("Used Car Vehicle Cost", cost_name):
				frappe.delete_doc("Used Car Vehicle Cost", cost_name, force=True)
		if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
			frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True)
		frappe.db.commit()


def _restricted_doc_counts():
	return {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
