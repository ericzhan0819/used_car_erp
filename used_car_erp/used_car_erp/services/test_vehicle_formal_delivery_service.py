import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from used_car_erp.used_car_erp.services.vehicle_formal_delivery_service import (
	RESTRICTED_FORMAL_DELIVERY_DOCTYPES,
	preflight_formal_delivery_submit,
	verify_formal_delivery_submit_preflight_service,
)


class TestVehicleFormalDeliveryService(FrappeTestCase):
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

	def test_final_check_blocked_blocks_preflight(self):
		vehicle = self._make_complete_vehicle(sales_invoice=None)

		result = preflight_formal_delivery_submit(vehicle.name)

		self.assertFalse(result["ready"])
		self.assertEqual(result["status"], "blocked")
		self.assertIn("交車前最終檢查尚未通過", " ".join(result["blocked_reasons"]))

	def test_final_check_warning_blocks_preflight(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(
			sales_invoice=invoice.name,
			vehicle_tax_mode="待確認",
			tax_review_status="待確認",
		)

		result = preflight_formal_delivery_submit(vehicle.name)

		self.assertFalse(result["ready"])
		self.assertEqual(result["status"], "blocked")
		self.assertIn("交車前最終檢查仍有待確認項目", " ".join(result["blocked_reasons"]))

	def test_sales_invoice_docstatus_not_draft_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=1)
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)

		result = preflight_formal_delivery_submit(vehicle.name)

		self.assertFalse(result["ready"])
		self.assertEqual(result["status"], "blocked")

	def test_update_stock_not_enabled_is_blocked(self):
		invoice = self._make_sales_invoice_stub(update_stock=0)
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)

		result = preflight_formal_delivery_submit(vehicle.name)

		self.assertFalse(result["ready"])
		self.assertEqual(self._find_check(result, "sales_invoice_draft")["state"], "blocked")

	def test_amount_mismatch_is_blocked(self):
		invoice = self._make_sales_invoice_stub(grand_total=590000, item_amount=590000)
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name, sold_price=600000)

		result = preflight_formal_delivery_submit(vehicle.name)

		self.assertFalse(result["ready"])
		self.assertEqual(self._find_check(result, "amount_consistency")["state"], "blocked")

	def test_complete_data_is_ready(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)

		result = preflight_formal_delivery_submit(vehicle.name)

		self.assertTrue(result["ready"])
		self.assertEqual(result["status"], "ready")

	def test_preflight_does_not_create_formal_documents_or_change_status(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		before_counts = self._restricted_doc_counts()
		before_values = frappe.db.get_value(
			"Used Car Vehicle",
			vehicle.name,
			[
				"status",
				"formal_delivery_status",
				"formal_delivery_completed_at",
				"advance_settlement_journal_entry",
			],
			as_dict=True,
		)
		before_docstatus = frappe.db.get_value("Sales Invoice", invoice.name, "docstatus")

		preflight_formal_delivery_submit(vehicle.name)

		after_values = frappe.db.get_value(
			"Used Car Vehicle",
			vehicle.name,
			[
				"status",
				"formal_delivery_status",
				"formal_delivery_completed_at",
				"advance_settlement_journal_entry",
			],
			as_dict=True,
		)
		self.assertEqual(self._restricted_doc_counts(), before_counts)
		self.assertEqual(before_values, after_values)
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "docstatus"), before_docstatus)

	def test_verify_formal_delivery_submit_preflight_service(self):
		result = verify_formal_delivery_submit_preflight_service()

		self.assertEqual(result["status"], "blocked")

	def _make_complete_vehicle(
		self,
		sales_invoice,
		sold_price=600000,
		vehicle_tax_mode="15-1 特殊扣抵",
		tax_review_status="已確認",
	):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"TST-FORMAL-PREFLIGHT-{frappe.generate_hash(length=6)}",
				"vin": f"TST-FORMAL-PREFLIGHT-{frappe.generate_hash(length=10)}",
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
				"sold_price": sold_price,
				"total_cost": 500000,
				"gross_margin": sold_price - 500000,
				"vehicle_tax_mode": vehicle_tax_mode,
				"tax_review_status": tax_review_status,
			}
		).insert(ignore_links=True)
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _make_sales_invoice_stub(self, docstatus=0, update_stock=1, grand_total=600000, item_amount=600000):
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "TST-CUSTOMER",
				"company": "TST-COMPANY",
				"posting_date": "2026-01-01",
				"grand_total": grand_total,
				"outstanding_amount": grand_total,
				"update_stock": update_stock,
				"docstatus": docstatus,
				"items": [
					{
						"item_code": "TST-ITEM",
						"qty": 1,
						"rate": item_amount,
						"amount": item_amount,
						"serial_no": "TST-SERIAL",
						"warehouse": "TST-WAREHOUSE",
						"income_account": "TST-INCOME",
					},
				],
			}
		).insert(ignore_links=True, ignore_mandatory=True)
		self.created_invoices.append(invoice.name)
		return invoice

	def _find_check(self, result, key):
		return next(check for check in result["checks"] if check["key"] == key)

	def _restricted_doc_counts(self):
		counts = {}
		for doctype in RESTRICTED_FORMAL_DELIVERY_DOCTYPES:
			counts[doctype] = frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
		return counts
