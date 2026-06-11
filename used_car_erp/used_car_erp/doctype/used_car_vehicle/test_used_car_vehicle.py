import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate


class TestUsedCarVehicle(FrappeTestCase):
	def tearDown(self):
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

	def test_create_vehicle_ignores_manual_stock_no(self):
		period = nowdate().replace("-", "")[:6]

		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"stock_no": "TEST-MANUAL-001",
				"vin": f"TEST-AUTO-VIN-{frappe.generate_hash(length=10)}",
			}
		).insert()

		self.assertRegex(vehicle.stock_no, rf"^VH-{period}-\d{{4}}$")
		self.assertEqual(vehicle.name, vehicle.stock_no)
		self.assertNotEqual(vehicle.stock_no, "TEST-MANUAL-001")
		self.assertEqual(vehicle.status, "草稿")

	def test_stock_no_cannot_be_changed_after_insert(self):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"vin": f"TEST-AUTO-VIN-{frappe.generate_hash(length=10)}",
			}
		).insert()
		original_stock_no = vehicle.stock_no

		vehicle.stock_no = "TEST-MANUAL-CHANGE-001"
		with self.assertRaises(frappe.ValidationError):
			vehicle.save()

		vehicle.reload()
		self.assertEqual(vehicle.stock_no, original_stock_no)
