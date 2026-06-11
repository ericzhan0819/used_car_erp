import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate


class TestUsedCarVehicle(FrappeTestCase):
	def tearDown(self):
		frappe.delete_doc_if_exists("Used Car Vehicle", "TEST-VEHICLE-MANUAL-001", force=True)
		for name in frappe.get_all(
			"Used Car Vehicle",
			filters={"vin": ["like", "TEST-AUTO-VIN-%"]},
			pluck="name",
		):
			frappe.delete_doc("Used Car Vehicle", name, force=True)

	def test_create_vehicle_auto_generates_stock_no_and_default_status(self):
		period = nowdate().replace("-", "")[:6]
		prefix = f"VH-{period}-"

		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"vin": f"TEST-AUTO-VIN-{frappe.generate_hash(length=10)}",
			}
		).insert()

		self.assertTrue(vehicle.stock_no.startswith(prefix))
		self.assertRegex(vehicle.stock_no, rf"^VH-{period}-\d{{4}}$")
		self.assertEqual(vehicle.name, vehicle.stock_no)
		self.assertEqual(vehicle.status, "草稿")

	def test_create_vehicle_preserves_manual_stock_no(self):
		frappe.delete_doc_if_exists("Used Car Vehicle", "TEST-VEHICLE-MANUAL-001", force=True)

		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"stock_no": "TEST-VEHICLE-MANUAL-001",
				"vin": f"TEST-AUTO-VIN-{frappe.generate_hash(length=10)}",
			}
		).insert()

		self.assertEqual(vehicle.stock_no, "TEST-VEHICLE-MANUAL-001")
		self.assertEqual(vehicle.name, "TEST-VEHICLE-MANUAL-001")
		self.assertEqual(vehicle.status, "草稿")
