import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from used_car_erp.used_car_erp.services.vehicle_formal_delivery_service import (
	RESTRICTED_FORMAL_DELIVERY_DOCTYPES,
	preflight_formal_delivery_submit,
	submit_formal_delivery_sales_invoice,
	verify_formal_delivery_submit_preflight_service,
	verify_formal_delivery_sales_invoice_submit_service,
)
import used_car_erp.used_car_erp.services.vehicle_formal_delivery_service as formal_delivery_service


class TestVehicleFormalDeliveryService(FrappeTestCase):
	def setUp(self):
		self.created_vehicles = []
		self.created_invoices = []
		self._original_preflight = formal_delivery_service.preflight_formal_delivery_submit
		self._original_submit = Document.submit

	def tearDown(self):
		formal_delivery_service.preflight_formal_delivery_submit = self._original_preflight
		Document.submit = self._original_submit
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

	def test_submit_preflight_blocked_does_not_submit_or_change_vehicle(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		formal_delivery_service.preflight_formal_delivery_submit = lambda vehicle_name: {
			"vehicle": vehicle_name,
			"ready": False,
			"status": "blocked",
			"blocked_reasons": ["final checklist blocked"],
		}

		result = submit_formal_delivery_sales_invoice(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "docstatus"), 0)
		self.assertEqual(frappe.db.get_value("Used Car Vehicle", vehicle.name, "formal_delivery_status"), vehicle.formal_delivery_status)

	def test_submit_sales_invoice_not_draft_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=1)
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._force_submit_preflight_ready()

		result = submit_formal_delivery_sales_invoice(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(frappe.db.get_value("Used Car Vehicle", vehicle.name, "formal_delivery_status"), vehicle.formal_delivery_status)

	def test_submit_update_stock_not_enabled_is_blocked(self):
		invoice = self._make_sales_invoice_stub(update_stock=0)
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._force_submit_preflight_ready()

		result = submit_formal_delivery_sales_invoice(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "docstatus"), 0)
		self.assertEqual(frappe.db.get_value("Used Car Vehicle", vehicle.name, "formal_delivery_status"), vehicle.formal_delivery_status)

	def test_submit_amount_mismatch_is_blocked(self):
		invoice = self._make_sales_invoice_stub(grand_total=590000, item_amount=590000)
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name, sold_price=600000)
		self._force_submit_preflight_ready()

		result = submit_formal_delivery_sales_invoice(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "docstatus"), 0)
		self.assertEqual(frappe.db.get_value("Used Car Vehicle", vehicle.name, "formal_delivery_status"), vehicle.formal_delivery_status)

	def test_submit_success_submits_invoice_and_marks_vehicle(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._force_submit_preflight_ready()
		self._patch_sales_invoice_submit_to_mark_submitted()

		result = submit_formal_delivery_sales_invoice(vehicle.name, note="Phase 3B test")

		self.assertEqual(result["status"], "submitted")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice.name, "docstatus"), 1)
		vehicle_values = frappe.db.get_value(
			"Used Car Vehicle",
			vehicle.name,
			["formal_delivery_status", "formal_delivery_posting_date", "formal_delivery_note"],
			as_dict=True,
		)
		self.assertEqual(vehicle_values.formal_delivery_status, "銷售發票已提交")
		self.assertEqual(str(vehicle_values.formal_delivery_posting_date), "2026-01-01")
		self.assertEqual(vehicle_values.formal_delivery_note, "Phase 3B test")

	def test_submit_success_does_not_create_restricted_documents_or_mark_completed(self):
		invoice = self._make_sales_invoice_stub()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		before_counts = self._restricted_doc_counts()
		reservation_before = vehicle.completed_reservation
		self._force_submit_preflight_ready()
		self._patch_sales_invoice_submit_to_mark_submitted()

		submit_formal_delivery_sales_invoice(vehicle.name)

		vehicle_values = frappe.db.get_value(
			"Used Car Vehicle",
			vehicle.name,
			[
				"formal_delivery_completed_at",
				"formal_delivery_completed_by",
				"advance_settlement_journal_entry",
			],
			as_dict=True,
		)
		self.assertEqual(self._restricted_doc_counts(), before_counts)
		self.assertFalse(vehicle_values.formal_delivery_completed_at)
		self.assertFalse(vehicle_values.formal_delivery_completed_by)
		self.assertFalse(vehicle_values.advance_settlement_journal_entry)
		self.assertEqual(frappe.db.get_value("Used Car Vehicle", vehicle.name, "completed_reservation"), reservation_before)

	def test_verify_formal_delivery_sales_invoice_submit_service(self):
		result = verify_formal_delivery_sales_invoice_submit_service()

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

	def _force_submit_preflight_ready(self):
		formal_delivery_service.preflight_formal_delivery_submit = lambda vehicle_name: {
			"vehicle": vehicle_name,
			"ready": True,
			"status": "ready",
			"blocked_reasons": [],
		}

	def _patch_sales_invoice_submit_to_mark_submitted(self):
		def fake_submit(invoice_doc):
			# 測試只驗證本 app 的 mutation 邊界；ERPNext 原生 ledger/stock side effect 由整合環境負責。
			invoice_doc.db_set("docstatus", 1, update_modified=True)
			invoice_doc.docstatus = 1

		Document.submit = fake_submit

	def _restricted_doc_counts(self):
		counts = {}
		for doctype in RESTRICTED_FORMAL_DELIVERY_DOCTYPES:
			counts[doctype] = frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
		return counts
