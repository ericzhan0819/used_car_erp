import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService
from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService
from used_car_erp.used_car_erp.services.vehicle_money_flow_service import verify_vehicle_money_flow_voucher_service
from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


class TestVehicleMoneyFlowService(FrappeTestCase):
	def setUp(self):
		self.intake_service = VehicleIntakeService()
		self.listing_service = VehicleListingService()
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
