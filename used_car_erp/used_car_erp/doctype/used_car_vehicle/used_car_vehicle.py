import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class UsedCarVehicle(Document):
	def before_insert(self):
		if self.stock_no:
			return

		self.stock_no = _get_next_stock_no()


def _get_next_stock_no():
	period = nowdate().replace("-", "")[:6]
	prefix = f"VH-{period}-"
	rows = frappe.db.sql(
		"""
		select stock_no
		from `tabUsed Car Vehicle`
		where stock_no like %s
		""",
		(f"{prefix}%",),
		as_dict=True,
	)

	max_number = 0
	for row in rows:
		try:
			max_number = max(max_number, int(row.stock_no.replace(prefix, "", 1)))
		except (TypeError, ValueError):
			# 避免歷史資料或手動編號格式不正確時，中斷新增車輛流程。
			continue

	return f"{prefix}{max_number + 1:04d}"


def verify_test_vehicle_insert():
	# 這個函式只供 bench execute 做部署後驗證，避免在正式資料中留下測試車輛。
	period = nowdate().replace("-", "")[:6]
	auto_number_prefix = f"VH-{period}-"
	vehicle = frappe.get_doc(
		{
			"doctype": "Used Car Vehicle",
			"vin": f"VERIFY-{frappe.generate_hash(length=10)}",
		}
	).insert()

	result = {
		"name": vehicle.name,
		"stock_no": vehicle.stock_no,
		"status": vehicle.status,
		"auto_number_prefix": auto_number_prefix,
		"doctype_exists": frappe.db.exists("DocType", "Used Car Vehicle"),
	}
	if not vehicle.stock_no.startswith(auto_number_prefix):
		frappe.throw("Used Car Vehicle stock_no was not auto-generated with the expected prefix.")
	if vehicle.name != vehicle.stock_no:
		frappe.throw("Used Car Vehicle name does not match stock_no.")
	if vehicle.status != "草稿":
		frappe.throw("Used Car Vehicle status default is not 草稿.")

	frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
	frappe.db.commit()
	return result
