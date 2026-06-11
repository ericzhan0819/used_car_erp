import frappe
from frappe.model.document import Document


class UsedCarVehicle(Document):
	pass


def verify_test_vehicle_insert():
	# 這個函式只供 bench execute 做部署後驗證，避免在正式資料中留下測試車輛。
	frappe.delete_doc_if_exists("Used Car Vehicle", "TEST-VEHICLE-001", force=True)
	vehicle = frappe.get_doc(
		{
			"doctype": "Used Car Vehicle",
			"stock_no": "TEST-VEHICLE-001",
			"vin": "TEST-VIN-001",
		}
	).insert()

	result = {
		"name": vehicle.name,
		"status": vehicle.status,
		"doctype_exists": frappe.db.exists("DocType", "Used Car Vehicle"),
	}
	frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
	frappe.db.commit()
	return result
