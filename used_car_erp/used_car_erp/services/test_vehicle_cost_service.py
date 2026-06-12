import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from used_car_erp.used_car_erp.services.vehicle_cost_service import (
	RESTRICTED_ACCOUNTING_DOCTYPES,
	recalculate_vehicle_cost_summary,
	verify_vehicle_cost_summary_service,
)


class TestVehicleCostService(FrappeTestCase):
	def setUp(self):
		self.created_costs = []
		self.created_vehicles = []

	def tearDown(self):
		for cost_name in reversed(self.created_costs):
			if frappe.db.exists("Used Car Vehicle Cost", cost_name):
				frappe.delete_doc("Used Car Vehicle Cost", cost_name, force=True)
		for vehicle_name in reversed(self.created_vehicles):
			if frappe.db.exists("Used Car Vehicle", vehicle_name):
				frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True)
		frappe.db.commit()

	def test_capitalized_cost_updates_vehicle_total_cost(self):
		vehicle = self._make_vehicle(purchase_price=500000)
		self._make_cost(vehicle.name, amount=20000, capitalization_mode="單車成本")

		vehicle.reload()
		self.assertEqual(vehicle.total_cost, 520000)

	def test_excluded_cost_does_not_update_vehicle_total_cost(self):
		vehicle = self._make_vehicle(purchase_price=500000)
		self._make_cost(vehicle.name, amount=10000, capitalization_mode="一般營業費用")

		vehicle.reload()
		self.assertEqual(vehicle.total_cost, 500000)

	def test_sold_price_calculates_gross_margin(self):
		vehicle = self._make_vehicle(purchase_price=500000, sold_price=600000)
		self._make_cost(vehicle.name, amount=20000, capitalization_mode="單車成本")

		vehicle.reload()
		self.assertEqual(vehicle.gross_margin, 80000)

	def test_negative_amount_is_blocked(self):
		vehicle = self._make_vehicle(purchase_price=500000)

		with self.assertRaises(frappe.ValidationError) as failure:
			self._make_cost(vehicle.name, amount=-1, capitalization_mode="單車成本")
		self.assertIn("成本金額不可為負數。", str(failure.exception))

	def test_recalculate_does_not_create_formal_documents(self):
		vehicle = self._make_vehicle(purchase_price=500000, sold_price=600000)
		self._make_cost(vehicle.name, amount=20000, capitalization_mode="單車成本")
		before_counts = self._restricted_doc_counts()

		recalculate_vehicle_cost_summary(vehicle.name)

		self.assertEqual(self._restricted_doc_counts(), before_counts)

	def test_verify_vehicle_cost_summary_service(self):
		result = verify_vehicle_cost_summary_service()

		self.assertEqual(result["total_cost"], 520000)
		self.assertEqual(result["gross_margin"], 80000)

	def _make_vehicle(self, purchase_price=0, sold_price=0):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"TST-COST-{frappe.generate_hash(length=6)}",
				"vin": f"TST-COST-{frappe.generate_hash(length=10)}",
				"purchase_price": purchase_price,
				"sold_price": sold_price,
			}
		).insert()
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _make_cost(self, vehicle_name, amount, capitalization_mode):
		cost = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle Cost",
				"vehicle": vehicle_name,
				"cost_date": nowdate(),
				"cost_category": "維修",
				"amount": amount,
				"capitalization_mode": capitalization_mode,
			}
		).insert()
		self.created_costs.append(cost.name)
		return cost

	def _restricted_doc_counts(self):
		return {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
