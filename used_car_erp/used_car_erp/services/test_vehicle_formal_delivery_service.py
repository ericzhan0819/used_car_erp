import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from used_car_erp.used_car_erp.services.vehicle_formal_delivery_service import (
	RESTRICTED_FORMAL_DELIVERY_DOCTYPES,
	create_advance_settlement_journal_entry_draft,
	preflight_formal_delivery_submit,
	submit_formal_delivery_sales_invoice,
	verify_advance_settlement_journal_entry_draft_service,
	verify_formal_delivery_submit_preflight_service,
	verify_formal_delivery_sales_invoice_submit_service,
)
import used_car_erp.used_car_erp.services.vehicle_formal_delivery_service as formal_delivery_service


class TestVehicleFormalDeliveryService(FrappeTestCase):
	def setUp(self):
		self.created_vehicles = []
		self.created_invoices = []
		self.created_journal_entries = []
		self._original_preflight = formal_delivery_service.preflight_formal_delivery_submit
		self._original_submit = Document.submit
		self._original_get_account_values = formal_delivery_service._get_account_values

	def tearDown(self):
		formal_delivery_service.preflight_formal_delivery_submit = self._original_preflight
		Document.submit = self._original_submit
		formal_delivery_service._get_account_values = self._original_get_account_values
		for vehicle_name in reversed(self.created_vehicles):
			if frappe.db.exists("Used Car Vehicle", vehicle_name):
				frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True, ignore_permissions=True)
		for journal_entry_name in reversed(self.created_journal_entries):
			if frappe.db.exists("Journal Entry", journal_entry_name):
				frappe.delete_doc("Journal Entry", journal_entry_name, force=True, ignore_permissions=True)
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

	def test_advance_settlement_sales_invoice_not_submitted_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=0, debit_to="TST-RECEIVABLE")
		deposit_je = self._make_advance_source_journal_entry()
		final_je = self._make_advance_source_journal_entry()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._set_vehicle_phase_3c_links(vehicle, deposit_je, final_je)
		before_count = frappe.db.count("Journal Entry")

		result = create_advance_settlement_journal_entry_draft(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(frappe.db.count("Journal Entry"), before_count)
		self.assertFalse(frappe.db.get_value("Used Car Vehicle", vehicle.name, "advance_settlement_journal_entry"))

	def test_advance_settlement_wrong_formal_status_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=1, debit_to="TST-RECEIVABLE")
		deposit_je = self._make_advance_source_journal_entry()
		final_je = self._make_advance_source_journal_entry()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._set_vehicle_phase_3c_links(vehicle, deposit_je, final_je, formal_delivery_status="銷售發票草稿")

		result = create_advance_settlement_journal_entry_draft(vehicle.name)

		self.assertEqual(result["status"], "blocked")

	def test_advance_settlement_existing_journal_entry_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=1, debit_to="TST-RECEIVABLE")
		deposit_je = self._make_advance_source_journal_entry()
		final_je = self._make_advance_source_journal_entry()
		existing_je = self._make_advance_source_journal_entry(docstatus=0)
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._set_vehicle_phase_3c_links(vehicle, deposit_je, final_je, advance_settlement_journal_entry=existing_je.name)
		before_count = frappe.db.count("Journal Entry")

		result = create_advance_settlement_journal_entry_draft(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertEqual(frappe.db.count("Journal Entry"), before_count)

	def test_advance_settlement_missing_accounting_links_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=1, debit_to="TST-RECEIVABLE")
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._set_vehicle_phase_3c_links(vehicle, None, None)

		result = create_advance_settlement_journal_entry_draft(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertIn("訂金或尾款入帳連結尚未完整", " ".join(result["blocked_reasons"]))

	def test_advance_settlement_missing_debit_to_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=1, debit_to=None)
		deposit_je = self._make_advance_source_journal_entry()
		final_je = self._make_advance_source_journal_entry()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._set_vehicle_phase_3c_links(vehicle, deposit_je, final_je)

		result = create_advance_settlement_journal_entry_draft(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertIn("Sales Invoice 應收帳款科目缺失", " ".join(result["blocked_reasons"]))

	def test_advance_settlement_liability_account_unresolved_is_blocked(self):
		invoice = self._make_sales_invoice_stub(docstatus=1, debit_to="TST-RECEIVABLE")
		deposit_je = self._make_advance_source_journal_entry(liability_account="TST-BANK")
		final_je = self._make_advance_source_journal_entry(liability_account="TST-BANK")
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._set_vehicle_phase_3c_links(vehicle, deposit_je, final_je)

		result = create_advance_settlement_journal_entry_draft(vehicle.name)

		self.assertEqual(result["status"], "blocked")
		self.assertIn("無法從訂金 / 尾款正式會計傳票解析預收款科目", " ".join(result["blocked_reasons"]))

	def test_advance_settlement_success_creates_journal_entry_draft(self):
		invoice = self._make_sales_invoice_stub(docstatus=1, debit_to="TST-RECEIVABLE")
		deposit_je = self._make_advance_source_journal_entry()
		final_je = self._make_advance_source_journal_entry()
		vehicle = self._make_complete_vehicle(sales_invoice=invoice.name)
		self._set_vehicle_phase_3c_links(vehicle, deposit_je, final_je)
		before_forbidden_counts = self._forbidden_phase_3c_doc_counts()

		result = create_advance_settlement_journal_entry_draft(vehicle.name, note="Phase 3C test")

		self.assertEqual(result["status"], "draft_created")
		journal_entry = frappe.get_doc("Journal Entry", result["journal_entry"])
		if journal_entry.name not in self.created_journal_entries:
			self.created_journal_entries.append(journal_entry.name)
		self.assertEqual(journal_entry.docstatus, 0)
		self.assertEqual(journal_entry.accounts[0].account, "TST-ADVANCE-LIABILITY")
		self.assertEqual(journal_entry.accounts[1].account, "TST-RECEIVABLE")
		self.assertEqual(journal_entry.accounts[0].debit_in_account_currency, journal_entry.accounts[1].credit_in_account_currency)
		vehicle_values = frappe.db.get_value(
			"Used Car Vehicle",
			vehicle.name,
			[
				"advance_settlement_journal_entry",
				"formal_delivery_status",
				"formal_delivery_completed_at",
				"formal_delivery_completed_by",
			],
			as_dict=True,
		)
		self.assertEqual(vehicle_values.advance_settlement_journal_entry, journal_entry.name)
		self.assertEqual(vehicle_values.formal_delivery_status, "預收款沖轉草稿")
		self.assertFalse(vehicle_values.formal_delivery_completed_at)
		self.assertFalse(vehicle_values.formal_delivery_completed_by)
		self.assertEqual(self._forbidden_phase_3c_doc_counts(), before_forbidden_counts)

	def test_verify_advance_settlement_journal_entry_draft_service(self):
		result = verify_advance_settlement_journal_entry_draft_service()

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

	def _make_sales_invoice_stub(self, docstatus=0, update_stock=1, grand_total=600000, item_amount=600000, debit_to=None):
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "TST-CUSTOMER",
				"company": "TST-COMPANY",
				"posting_date": "2026-01-01",
				"grand_total": grand_total,
				"outstanding_amount": grand_total,
				"debit_to": debit_to,
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

	def _make_advance_source_journal_entry(self, docstatus=1, liability_account="TST-ADVANCE-LIABILITY"):
		self._patch_account_values()
		journal_entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": "TST-COMPANY",
				"posting_date": "2026-01-01",
				"docstatus": docstatus,
				"accounts": [
					{
						"account": "TST-BANK",
						"debit_in_account_currency": 300000,
						"credit_in_account_currency": 0,
					},
					{
						"account": liability_account,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": 300000,
					},
				],
			}
		).insert(ignore_links=True, ignore_mandatory=True)
		if docstatus:
			journal_entry.db_set("docstatus", docstatus, update_modified=False)
			journal_entry.docstatus = docstatus
		if journal_entry.name not in self.created_journal_entries:
			self.created_journal_entries.append(journal_entry.name)
		return journal_entry

	def _set_vehicle_phase_3c_links(
		self,
		vehicle,
		deposit_je,
		final_je,
		formal_delivery_status="銷售發票已提交",
		advance_settlement_journal_entry=None,
	):
		vehicle.db_set("formal_delivery_status", formal_delivery_status, update_modified=False)
		vehicle.db_set("deposit_money_flow", "TST-DEPOSIT-FLOW", update_modified=False)
		vehicle.db_set("deposit_voucher_draft", "TST-DEPOSIT-DRAFT", update_modified=False)
		vehicle.db_set("deposit_journal_entry", deposit_je.name if deposit_je else None, update_modified=False)
		vehicle.db_set("final_money_flow", "TST-FINAL-FLOW", update_modified=False)
		vehicle.db_set("final_voucher_draft", "TST-FINAL-DRAFT", update_modified=False)
		vehicle.db_set("final_journal_entry", final_je.name if final_je else None, update_modified=False)
		vehicle.db_set("advance_settlement_journal_entry", advance_settlement_journal_entry, update_modified=False)
		vehicle.reload()
		return vehicle

	def _patch_account_values(self):
		def fake_get_account_values(account_name):
			mapping = {
				"TST-BANK": ("Bank", "Asset"),
				"TST-RECEIVABLE": ("Receivable", "Asset"),
				"TST-ADVANCE-LIABILITY": (None, "Liability"),
			}
			return mapping.get(account_name, (None, None))

		formal_delivery_service._get_account_values = fake_get_account_values

	def _forbidden_phase_3c_doc_counts(self):
		counts = {}
		for doctype in ("Payment Entry", "Delivery Note", "Stock Entry", "Tax Summary"):
			counts[doctype] = frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
		return counts

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
