import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from used_car_erp.used_car_erp.services.vehicle_cost_service import RESTRICTED_ACCOUNTING_DOCTYPES
from used_car_erp.used_car_erp.services.vehicle_profit_tax_estimate_service import (
	get_vehicle_profit_tax_estimate,
	verify_vehicle_profit_tax_estimate_service,
)


class TestVehicleProfitTaxEstimateService(FrappeTestCase):
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

	def test_15_1_special_input_credit_estimate(self):
		vehicle = self._make_vehicle(
			purchase_price=500000,
			sold_price=600000,
			vehicle_tax_mode="15-1 特殊扣抵",
		)

		result = get_vehicle_profit_tax_estimate(vehicle.name)
		expected_output_vat = round(600000 * 5 / 105)
		expected_raw_credit = round(500000 * 5 / 105)

		self.assertEqual(result["estimated_output_vat"], expected_output_vat)
		self.assertEqual(result["estimated_15_1_input_credit_raw"], expected_raw_credit)
		self.assertEqual(result["estimated_15_1_input_credit"], min(expected_raw_credit, expected_output_vat))
		self.assertEqual(result["estimated_vat_payable"], expected_output_vat - min(expected_raw_credit, expected_output_vat))

	def test_15_1_input_credit_does_not_exceed_output_vat(self):
		vehicle = self._make_vehicle(
			purchase_price=700000,
			sold_price=600000,
			vehicle_tax_mode="15-1 特殊扣抵",
		)

		result = get_vehicle_profit_tax_estimate(vehicle.name)

		self.assertLessEqual(result["estimated_15_1_input_credit"], result["estimated_output_vat"])
		self.assertGreaterEqual(result["estimated_vat_payable"], 0)

	def test_general_invoice_input_credit_includes_deductible_cost_vat(self):
		vehicle = self._make_vehicle(
			purchase_price=500000,
			sold_price=600000,
			vehicle_tax_mode="一般發票扣抵",
		)
		self._make_cost(vehicle.name, amount=10500, tax_deductibility="可扣抵")

		result = get_vehicle_profit_tax_estimate(vehicle.name)
		expected_credit = round(500000 * 5 / 105) + round(10500 * 5 / 105)

		self.assertEqual(result["estimated_general_input_credit"], expected_credit)
		self.assertEqual(result["estimated_input_credit"], expected_credit)

	def test_pending_tax_mode_requires_confirmation(self):
		vehicle = self._make_vehicle(
			purchase_price=500000,
			sold_price=600000,
			vehicle_tax_mode="待確認",
		)

		result = get_vehicle_profit_tax_estimate(vehicle.name)

		self.assertEqual(result["estimated_input_credit"], 0)
		self.assertEqual(result["tax_estimate_status"], "需確認")

	def test_estimate_does_not_create_formal_documents(self):
		vehicle = self._make_vehicle(
			purchase_price=500000,
			sold_price=600000,
			vehicle_tax_mode="15-1 特殊扣抵",
		)
		before_counts = self._restricted_doc_counts()

		get_vehicle_profit_tax_estimate(vehicle.name)

		self.assertEqual(self._restricted_doc_counts(), before_counts)

	def test_verify_vehicle_profit_tax_estimate_service(self):
		result = verify_vehicle_profit_tax_estimate_service()

		self.assertEqual(result["total_cost"], 520000)
		self.assertEqual(result["gross_margin"], 80000)

	def _make_vehicle(self, purchase_price=0, sold_price=0, vehicle_tax_mode="待確認"):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"TST-PROFIT-TAX-{frappe.generate_hash(length=6)}",
				"vin": f"TST-PROFIT-TAX-{frappe.generate_hash(length=10)}",
				"purchase_price": purchase_price,
				"sold_price": sold_price,
				"vehicle_tax_mode": vehicle_tax_mode,
			}
		).insert()
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _make_cost(self, vehicle_name, amount, tax_deductibility):
		cost = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle Cost",
				"vehicle": vehicle_name,
				"cost_date": nowdate(),
				"cost_category": "維修",
				"amount": amount,
				"capitalization_mode": "單車成本",
				"tax_deductibility": tax_deductibility,
			}
		).insert()
		self.created_costs.append(cost.name)
		return cost

	def _restricted_doc_counts(self):
		return {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
