import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService
from used_car_erp.used_car_erp.services.vehicle_money_flow_service import (
	VehicleMoneyFlowService,
	verify_vehicle_money_flow_voucher_service,
)
from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService
from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


class TestVehicleMoneyFlowService(FrappeTestCase):
	def setUp(self):
		self.intake_service = VehicleIntakeService()
		self.listing_service = VehicleListingService()
		self.money_flow_service = VehicleMoneyFlowService()
		self.reservation_service = VehicleReservationService()
		self.voucher_service = VehicleVoucherService()
		self.created_vehicles = []
		self.created_items = []
		self.created_stock_entries = []
		self.created_serial_nos = []
		self.created_reservations = []
		self.created_money_flows = []
		self.created_voucher_drafts = []
		self.created_journal_entries = []
		self.created_customers = []

	def tearDown(self):
		for reservation_name in reversed(self.created_reservations):
			if frappe.db.exists("Used Car Reservation", reservation_name):
				updates = {}
				meta = frappe.get_meta("Used Car Reservation")
				for fieldname in (
					"money_flow",
					"voucher_draft",
					"journal_entry",
					"final_money_flow",
					"final_voucher_draft",
					"final_journal_entry",
				):
					if meta.has_field(fieldname):
						updates[fieldname] = None
				if updates:
					frappe.db.set_value("Used Car Reservation", reservation_name, updates)
		for journal_entry_name in reversed(self.created_journal_entries):
			if frappe.db.exists("Journal Entry", journal_entry_name):
				journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
				if journal_entry.docstatus == 1:
					journal_entry.cancel()
				elif journal_entry.docstatus == 0:
					frappe.delete_doc("Journal Entry", journal_entry_name, force=True)
		for draft_name in reversed(self.created_voucher_drafts):
			if frappe.db.exists("Used Car Voucher Draft", draft_name):
				frappe.delete_doc("Used Car Voucher Draft", draft_name, force=True)
		for money_flow_name in reversed(self.created_money_flows):
			if frappe.db.exists("Used Car Money Flow", money_flow_name):
				frappe.delete_doc("Used Car Money Flow", money_flow_name, force=True)
		for reservation_name in reversed(self.created_reservations):
			if frappe.db.exists("Used Car Reservation", reservation_name):
				frappe.delete_doc("Used Car Reservation", reservation_name, force=True)
		for stock_entry_name in reversed(self.created_stock_entries):
			if frappe.db.exists("Stock Entry", stock_entry_name):
				stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
				if stock_entry.docstatus == 1:
					stock_entry.cancel()
		for vehicle_name in reversed(self.created_vehicles):
			if frappe.db.exists("Used Car Vehicle", vehicle_name):
				frappe.db.set_value("Used Car Vehicle", vehicle_name, {"serial_no": None, "stock_entry": None, "item": None})
				frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True)
		for serial_no in reversed(self.created_serial_nos):
			if frappe.db.exists("Serial No", serial_no):
				try:
					frappe.delete_doc("Serial No", serial_no, force=True)
				except Exception:
					pass
		for item_name in reversed(self.created_items):
			if frappe.db.exists("Item", item_name):
				try:
					frappe.delete_doc("Item", item_name, force=True)
				except Exception:
					pass
		for customer_name in reversed(self.created_customers):
			if frappe.db.exists("Customer", customer_name):
				try:
					frappe.delete_doc("Customer", customer_name, force=True)
				except Exception:
					pass
		frappe.db.commit()

	def test_create_reservation_creates_money_flow(self):
		result = self._create_reservation_for_listed_vehicle()
		self.assertTrue(frappe.db.exists("Used Car Money Flow", result.get("money_flow")))

	def test_create_reservation_creates_voucher_draft(self):
		result = self._create_reservation_for_listed_vehicle()
		self.assertTrue(frappe.db.exists("Used Car Voucher Draft", result.get("voucher_draft")))

	def test_create_reservation_does_not_create_journal_entry(self):
		before_count = frappe.db.count("Journal Entry")
		self._create_reservation_for_listed_vehicle()
		self.assertEqual(frappe.db.count("Journal Entry"), before_count)

	def test_create_reservation_does_not_create_restricted_documents(self):
		before_counts = self._restricted_doc_counts()
		self._create_reservation_for_listed_vehicle()
		after_counts = self._restricted_doc_counts()
		self.assertEqual(after_counts["Payment Entry"], before_counts["Payment Entry"])
		self.assertEqual(after_counts["Sales Invoice"], before_counts["Sales Invoice"])
		self.assertEqual(after_counts["Delivery Note"], before_counts["Delivery Note"])
		self.assertEqual(after_counts["Stock Entry"], before_counts["Stock Entry"])

	def test_voucher_draft_is_balanced(self):
		result = self._create_reservation_for_listed_vehicle()
		draft = frappe.get_doc("Used Car Voucher Draft", result.get("voucher_draft"))
		self.assertEqual(draft.total_debit, draft.total_credit)
		self.assertEqual(draft.difference, 0)

	def test_confirm_creates_journal_entry(self):
		result = self._create_reservation_for_listed_vehicle()
		before_count = frappe.db.count("Journal Entry")
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		self.assertEqual(frappe.db.count("Journal Entry"), before_count + 1)

	def test_confirm_marks_money_flow_posted(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		money_flow = frappe.get_doc("Used Car Money Flow", result.get("money_flow"))
		self.assertEqual(money_flow.status, "已入帳")

	def test_confirm_marks_voucher_draft_posted(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		draft = frappe.get_doc("Used Car Voucher Draft", result.get("voucher_draft"))
		self.assertEqual(draft.status, "已入帳")

	def test_posted_draft_cannot_confirm_again(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		self.assertRaises(frappe.ValidationError, self.voucher_service.confirm_voucher_draft, result.get("voucher_draft"), "AGAIN")

	def test_pending_draft_can_be_rejected(self):
		result = self._create_reservation_for_listed_vehicle()
		reject_result = self.voucher_service.reject_voucher_draft(result.get("voucher_draft"), "TEST REJECT")
		self.assertEqual(reject_result.get("status"), "已退回")

	def test_pending_or_rejected_draft_can_be_voided(self):
		result = self._create_reservation_for_listed_vehicle()
		self.voucher_service.reject_voucher_draft(result.get("voucher_draft"), "TEST REJECT")
		void_result = self.voucher_service.void_voucher_draft(result.get("voucher_draft"), "TEST VOID")
		self.assertEqual(void_result.get("status"), "已作廢")

	def test_posted_draft_cannot_be_voided(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		self.assertRaises(frappe.ValidationError, self.voucher_service.void_voucher_draft, result.get("voucher_draft"), "TEST VOID")

	def test_unbalanced_draft_cannot_be_confirmed(self):
		result = self._create_reservation_for_listed_vehicle()
		draft = frappe.get_doc("Used Car Voucher Draft", result.get("voucher_draft"))
		draft.lines[0].debit = 1
		self.assertRaises(frappe.ValidationError, self.voucher_service._validate_draft_ready_for_confirm, draft)

	def test_create_final_payment_creates_money_flow_and_voucher_draft(self):
		result = self._create_reservation_for_listed_vehicle()
		final_result = self._create_final_payment_for_reservation(result.get("reservation"))
		money_flow = frappe.get_doc("Used Car Money Flow", final_result.get("money_flow"))
		draft = frappe.get_doc("Used Car Voucher Draft", final_result.get("voucher_draft"))
		self.assertEqual(money_flow.flow_type, "尾款收款")
		self.assertEqual(money_flow.status, "待審核")
		self.assertEqual(draft.status, "待審核")
		self.assertEqual(draft.total_debit, draft.total_credit)
		self.assertEqual(draft.difference, 0)

	def test_create_final_payment_does_not_create_restricted_documents(self):
		result = self._create_reservation_for_listed_vehicle()
		before_counts = self._restricted_doc_counts()
		before_journal_count = frappe.db.count("Journal Entry")
		self._create_final_payment_for_reservation(result.get("reservation"))
		after_counts = self._restricted_doc_counts()
		self.assertEqual(frappe.db.count("Journal Entry"), before_journal_count)
		self.assertEqual(after_counts["Payment Entry"], before_counts["Payment Entry"])
		self.assertEqual(after_counts["Sales Invoice"], before_counts["Sales Invoice"])
		self.assertEqual(after_counts["Delivery Note"], before_counts["Delivery Note"])
		self.assertEqual(after_counts["Stock Entry"], before_counts["Stock Entry"])

	def test_confirm_final_payment_updates_final_journal_entry(self):
		result = self._create_reservation_for_listed_vehicle()
		final_result = self._create_final_payment_for_reservation(result.get("reservation"))
		confirm_result = self.voucher_service.confirm_voucher_draft(final_result.get("voucher_draft"), "TEST FINAL CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))
		self.assertEqual(reservation.final_journal_entry, confirm_result.get("journal_entry"))

	def test_duplicate_final_payment_is_rejected(self):
		result = self._create_reservation_for_listed_vehicle()
		self._create_final_payment_for_reservation(result.get("reservation"))
		self.assertRaises(
			frappe.ValidationError,
			self.money_flow_service.create_final_payment_money_flow_from_reservation,
			result.get("reservation"),
			50000,
			"現金",
		)

	def test_delivery_preflight_rejects_missing_final_payment(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST DEPOSIT CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.preflight_delivery_for_active_reservation(result.get("vehicle_name"))
		self.assertIn("尚未建立尾款金流紀錄", str(failure.exception))

	def test_delivery_preflight_rejects_unposted_final_payment(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST DEPOSIT CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		self._create_final_payment_for_reservation(result.get("reservation"))

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.preflight_delivery_for_active_reservation(result.get("vehicle_name"))
		self.assertIn("尾款金流尚未入帳", str(failure.exception))

	def test_delivery_preflight_passes_after_deposit_and_final_posted(self):
		result = self._create_fully_posted_reservation()
		preflight = self.reservation_service.preflight_delivery_for_active_reservation(result.get("vehicle_name"))

		self.assertTrue(preflight.get("passed"))
		self.assertEqual(preflight.get("reservation"), result.get("reservation"))
		self.assertEqual(preflight.get("deposit_journal_entry"), result.get("deposit_journal_entry"))
		self.assertEqual(preflight.get("final_journal_entry"), result.get("final_journal_entry"))

	def test_delivery_preflight_does_not_create_restricted_documents(self):
		result = self._create_fully_posted_reservation()
		before_counts = self._restricted_doc_counts()
		self.reservation_service.preflight_delivery_for_active_reservation(result.get("vehicle_name"))
		after_counts = self._restricted_doc_counts()

		self.assertEqual(after_counts["Payment Entry"], before_counts["Payment Entry"])
		self.assertEqual(after_counts["Sales Invoice"], before_counts["Sales Invoice"])
		self.assertEqual(after_counts["Delivery Note"], before_counts["Delivery Note"])
		self.assertEqual(after_counts["Stock Entry"], before_counts["Stock Entry"])

	def test_delivery_preflight_keeps_vehicle_and_reservation_status(self):
		result = self._create_fully_posted_reservation()
		self.reservation_service.preflight_delivery_for_active_reservation(result.get("vehicle_name"))
		vehicle = frappe.get_doc("Used Car Vehicle", result.get("vehicle_name"))
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))

		self.assertEqual(vehicle.status, "保留中")
		self.assertEqual(reservation.status, "有效")

	def test_verify_service_cleans_core_test_documents(self):
		result = verify_vehicle_money_flow_voucher_service()
		self.assertTrue(result.get("voucher_draft_deleted"))
		self.assertTrue(result.get("money_flow_deleted"))
		self.assertTrue(result.get("reservation_deleted"))
		self.assertTrue(result.get("vehicle_deleted"))
		self.assertTrue(result.get("cleaned_up"))
		self.assertFalse(frappe.db.exists("Used Car Voucher Draft", result.get("voucher_draft")))
		self.assertFalse(frappe.db.exists("Used Car Money Flow", result.get("money_flow")))
		self.assertFalse(frappe.db.exists("Used Car Reservation", result.get("reservation")))
		self.assertFalse(frappe.db.exists("Used Car Vehicle", result.get("vehicle_name")))

	def _create_reservation_for_listed_vehicle(self):
		vehicle = self._make_listed_vehicle()
		result = self.reservation_service.create_reservation(
			vehicle_name=vehicle.name,
			customer_name=f"測試客戶{frappe.generate_hash(length=6)}",
			customer_phone=f"09{frappe.generate_hash(length=8)}",
			deposit_amount=10000,
			payment_method="現金",
		)
		self.created_reservations.append(result.get("reservation"))
		self.created_money_flows.append(result.get("money_flow"))
		self.created_voucher_drafts.append(result.get("voucher_draft"))
		self.created_customers.append(result.get("customer"))
		return result

	def _create_final_payment_for_reservation(self, reservation_name):
		result = self.money_flow_service.create_final_payment_money_flow_from_reservation(
			reservation_name=reservation_name,
			amount=50000,
			payment_method="現金",
			payment_reference="TEST FINAL",
		)
		self.created_money_flows.append(result.get("money_flow"))
		self.created_voucher_drafts.append(result.get("voucher_draft"))
		return result

	def _create_fully_posted_reservation(self):
		result = self._create_reservation_for_listed_vehicle()
		deposit_confirm = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST DEPOSIT CONFIRM")
		self.created_journal_entries.append(deposit_confirm.get("journal_entry"))
		final_result = self._create_final_payment_for_reservation(result.get("reservation"))
		final_confirm = self.voucher_service.confirm_voucher_draft(final_result.get("voucher_draft"), "TEST FINAL CONFIRM")
		self.created_journal_entries.append(final_confirm.get("journal_entry"))
		result.update(
			{
				"final_money_flow": final_result.get("money_flow"),
				"final_voucher_draft": final_result.get("voucher_draft"),
				"deposit_journal_entry": deposit_confirm.get("journal_entry"),
				"final_journal_entry": final_confirm.get("journal_entry"),
			}
		)
		return result

	def _make_vehicle(self):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"TST-MF-{frappe.generate_hash(length=6)}",
				"vin": f"TST-MF-{frappe.generate_hash(length=10)}",
				"purchase_price": 300000,
			}
		).insert()
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _make_listed_vehicle(self):
		vehicle = self._make_vehicle()
		intake_result = self.intake_service.complete_intake(vehicle.name)
		self.created_stock_entries.append(intake_result.get("stock_entry"))
		self.created_serial_nos.append(intake_result.get("serial_no"))
		self.created_items.append(intake_result.get("item"))
		self.listing_service.list_vehicle(vehicle.name)
		vehicle.reload()
		return vehicle

	def _restricted_doc_counts(self):
		return {
			"Stock Entry": frappe.db.count("Stock Entry"),
			"Payment Entry": frappe.db.count("Payment Entry"),
			"Sales Invoice": frappe.db.count("Sales Invoice"),
			"Delivery Note": frappe.db.count("Delivery Note"),
		}
