import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from used_car_erp.used_car_erp.services.vehicle_final_check_service import (
	RESTRICTED_FINAL_CHECK_DOCTYPES,
	get_sold_vehicle_final_check,
	verify_vehicle_final_check_service,
)


class TestVehicleFinalCheckService(FrappeTestCase):
	def setUp(self):
		self.created_vehicles = []
		self.created_invoices = []

	def tearDown(self):
		for vehicle_name in reversed(self.created_vehicles):
			if frappe.db.exists("Used Car Vehicle", vehicle_name):
				frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True, ignore_permissions=True)
		for invoice_name in reversed(self.created_invoices):
			if frappe.db.exists("Sales Invoice", invoice_name):
				frappe.delete_doc("Sales Invoice", invoice_name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def test_complete_data_is_ready(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)

		result = get_sold_vehicle_final_check(vehicle.name)

		self.assertEqual(result["status"], "ready")
		for key in self._required_check_keys():
			self.assertEqual(self._find_check(result, key)["state"], "ok")

	def test_missing_sales_invoice_is_blocked(self):
		vehicle = self._make_complete_vehicle(sales_invoice=None)

		result = get_sold_vehicle_final_check(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(self._find_check(result, "sales_invoice")["state"], "blocked")

	def test_pending_tax_metadata_is_warning(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(
			sales_invoice=invoice.name,
			vehicle_tax_mode="待確認",
			tax_review_status="待確認",
		)

		result = get_sold_vehicle_final_check(vehicle.name)

		self.assertEqual(result["status"], "warning")
		self.assertEqual(self._find_check(result, "tax_metadata")["state"], "warning")

	def test_final_check_does_not_create_formal_documents(self):
		vehicle = self._make_complete_vehicle(sales_invoice=None)
		before_counts = self._restricted_doc_counts()

		get_sold_vehicle_final_check(vehicle.name)

		self.assertEqual(self._restricted_doc_counts(), before_counts)

	def test_verify_vehicle_final_check_service(self):
		result = verify_vehicle_final_check_service()

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(self._find_check(result, "sales_invoice")["state"], "blocked")

	def _make_complete_vehicle(
		self,
		sales_invoice,
		vehicle_tax_mode="15-1 特殊扣抵",
		tax_review_status="已確認",
	):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"TST-FINAL-CHECK-{frappe.generate_hash(length=6)}",
				"vin": f"TST-FINAL-CHECK-{frappe.generate_hash(length=10)}",
				"status": "已售出",
				"completed_reservation": "TST-RESERVATION",
				"completed_at": now_datetime(),
				"completed_by": "Administrator",
				"deposit_money_flow": "TST-DEPOSIT-FLOW",
				"deposit_voucher_draft": "TST-DEPOSIT-DRAFT",
				"deposit_journal_entry": "TST-DEPOSIT-JE",
				"final_money_flow": "TST-FINAL-FLOW",
				"final_voucher_draft": "TST-FINAL-DRAFT",
				"final_journal_entry": "TST-FINAL-JE",
				"item": "TST-ITEM",
				"serial_no": "TST-SERIAL",
				"stock_warehouse": "TST-WAREHOUSE",
				"sales_invoice": sales_invoice,
				"purchase_price": 500000,
				"sold_price": 600000,
				"total_cost": 500000,
				"gross_margin": 100000,
				"vehicle_tax_mode": vehicle_tax_mode,
				"tax_review_status": tax_review_status,
			}
		).insert(ignore_links=True)
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _make_sales_invoice_stub(self, docstatus=0):
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "TST-CUSTOMER",
				"company": "TST-COMPANY",
				"posting_date": "2026-01-01",
				"grand_total": 600000,
				"outstanding_amount": 600000,
				"update_stock": 1,
				"docstatus": docstatus,
			}
		).insert(ignore_links=True, ignore_mandatory=True)
		self.created_invoices.append(invoice.name)
		return invoice

	def _find_check(self, result, key):
		return next(check for check in result["checks"] if check["key"] == key)

	def _required_check_keys(self):
		return (
			"completion",
			"deposit",
			"final_payment",
			"stock_link",
			"sales_invoice",
			"cost_summary",
			"profit_tax_estimate",
		)

	def _restricted_doc_counts(self):
		counts = {}
		for doctype in RESTRICTED_FINAL_CHECK_DOCTYPES:
			counts[doctype] = frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
		return counts
