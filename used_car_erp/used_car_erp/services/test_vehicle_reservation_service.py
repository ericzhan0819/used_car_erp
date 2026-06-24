import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService
from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService


class TestVehicleReservationService(FrappeTestCase):
	def setUp(self):
		self.service = VehicleReservationService()
		self.intake_service = VehicleIntakeService()
		self.listing_service = VehicleListingService()
		self.created_vehicles = []
		self.created_items = []
		self.created_stock_entries = []
		self.created_serial_nos = []
		self.created_reservations = []
		self.created_customers = []

	def tearDown(self):
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
				frappe.db.set_value(
					"Used Car Vehicle",
					vehicle_name,
					{"serial_no": None, "stock_entry": None, "item": None},
				)
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

	def test_create_reservation_allows_listed_to_reserved(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)
		vehicle.reload()

		self.assertEqual(result.get("previous_status"), "上架中")
		self.assertEqual(vehicle.status, "保留中")
		self.assertEqual(vehicle.sold_price, 60000)

	def test_create_reservation_creates_reservation_document(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))

		self.assertEqual(reservation.vehicle, vehicle.name)
		self.assertEqual(reservation.status, "有效")

	def test_create_reservation_can_create_or_link_customer(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)

		self.assertTrue(result.get("customer"))
		self.assertTrue(frappe.db.exists("Customer", result.get("customer")))

	def test_same_vehicle_cannot_have_second_active_reservation(self):
		vehicle = self._make_listed_vehicle()
		self._create_reservation(vehicle)

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle)

	def test_non_listed_vehicle_cannot_create_reservation(self):
		vehicle = self._make_stocked_vehicle()

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle)

	def test_unstocked_vehicle_cannot_create_reservation(self):
		vehicle = self._make_vehicle()
		frappe.db.set_value("Used Car Vehicle", vehicle.name, "status", "上架中")

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle)

	def test_deposit_amount_must_be_positive(self):
		vehicle = self._make_listed_vehicle()

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle, deposit_amount=0)

	def test_sold_price_must_be_positive(self):
		vehicle = self._make_listed_vehicle()

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle, sold_price=0)

	def test_deposit_amount_cannot_exceed_sold_price(self):
		vehicle = self._make_listed_vehicle()

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle, sold_price=10000, deposit_amount=10001)

	def test_customer_name_is_required(self):
		vehicle = self._make_listed_vehicle()

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle, customer_name="")

	def test_customer_phone_is_required(self):
		vehicle = self._make_listed_vehicle()

		self.assertRaises(frappe.ValidationError, self._create_reservation, vehicle, customer_phone="")

	def test_cancel_active_reservation_returns_vehicle_to_listed(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)

		cancel_result = self.service.cancel_active_reservation_for_vehicle(vehicle.name, "測試取消")
		vehicle.reload()
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))

		self.assertEqual(cancel_result.get("status"), "上架中")
		self.assertEqual(vehicle.status, "上架中")
		self.assertEqual(reservation.status, "已取消")

	def test_cancel_reservation_requires_reason(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)

		self.assertRaises(frappe.ValidationError, self.service.cancel_reservation, result.get("reservation"), "")

	def test_reservation_and_cancel_do_not_create_stock_entry(self):
		vehicle = self._make_listed_vehicle()
		before_count = frappe.db.count("Stock Entry")

		self._create_reservation(vehicle)
		self.service.cancel_active_reservation_for_vehicle(vehicle.name, "測試取消")

		self.assertEqual(frappe.db.count("Stock Entry"), before_count)

	def test_reservation_and_cancel_do_not_create_sales_payment_delivery_or_journal_documents(self):
		vehicle = self._make_listed_vehicle()
		before_counts = self._restricted_doc_counts()

		self._create_reservation(vehicle)
		self.service.cancel_active_reservation_for_vehicle(vehicle.name, "測試取消")

		self.assertEqual(self._restricted_doc_counts(), before_counts)

	def test_reservation_and_cancel_do_not_modify_serial_no(self):
		vehicle = self._make_listed_vehicle()
		before_modified = frappe.db.get_value("Serial No", vehicle.serial_no, "modified")

		self._create_reservation(vehicle)
		self.service.cancel_active_reservation_for_vehicle(vehicle.name, "測試取消")

		self.assertEqual(frappe.db.get_value("Serial No", vehicle.serial_no, "modified"), before_modified)

	def test_cancel_with_deposit_handling_voids_unposted_deposit_documents(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)
		before_journal_count = frappe.db.count("Journal Entry")

		cancel_result = self.service.cancel_active_reservation_with_deposit_handling(vehicle.name, "測試取消")
		vehicle.reload()
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))
		money_flow = frappe.get_doc("Used Car Money Flow", result.get("money_flow"))
		voucher_draft = frappe.get_doc("Used Car Voucher Draft", result.get("voucher_draft"))

		self.assertFalse(cancel_result.get("refund_required"))
		self.assertEqual(vehicle.status, "上架中")
		self.assertEqual(reservation.status, "已取消")
		self.assertEqual(money_flow.status, "已作廢")
		self.assertEqual(voucher_draft.status, "已作廢")
		self.assertEqual(frappe.db.count("Journal Entry"), before_journal_count)

	def test_cancel_with_deposit_handling_creates_refund_for_posted_deposit(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)
		from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService

		confirm_result = VehicleVoucherService().confirm_voucher_draft(result.get("voucher_draft"), "TEST DEPOSIT CONFIRM")
		before_journal_count = frappe.db.count("Journal Entry")

		cancel_result = self.service.cancel_active_reservation_with_deposit_handling(
			vehicle.name,
			"測試取消",
			refund_payment_method="現金",
			refund_reference="TEST REFUND",
		)
		vehicle.reload()
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))
		deposit_money_flow = frappe.get_doc("Used Car Money Flow", result.get("money_flow"))
		deposit_voucher_draft = frappe.get_doc("Used Car Voucher Draft", result.get("voucher_draft"))
		refund_money_flow = frappe.get_doc("Used Car Money Flow", cancel_result.get("refund_money_flow"))
		refund_voucher_draft = frappe.get_doc("Used Car Voucher Draft", cancel_result.get("refund_voucher_draft"))

		self.assertTrue(cancel_result.get("refund_required"))
		self.assertEqual(vehicle.status, "上架中")
		self.assertEqual(reservation.status, "已取消")
		self.assertEqual(deposit_money_flow.status, "已入帳")
		self.assertEqual(deposit_voucher_draft.status, "已入帳")
		self.assertEqual(refund_money_flow.flow_type, "退款")
		self.assertEqual(refund_money_flow.direction, "支出")
		self.assertEqual(refund_money_flow.status, "待審核")
		self.assertEqual(refund_voucher_draft.status, "待審核")
		self.assertEqual(frappe.db.count("Journal Entry"), before_journal_count)

		self.created_reservations.append(result.get("reservation"))
		self._cleanup_linked_doc("Used Car Voucher Draft", cancel_result.get("refund_voucher_draft"))
		self._cleanup_linked_doc("Used Car Money Flow", cancel_result.get("refund_money_flow"))
		self._cleanup_linked_doc("Journal Entry", confirm_result.get("journal_entry"))

	def test_cancel_with_deposit_handling_rejects_existing_final_payment(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_reservation(vehicle)
		VehicleReservationService().create_final_payment_for_active_reservation(vehicle.name, 50000, "現金")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.service.cancel_active_reservation_with_deposit_handling(vehicle.name, "測試取消")
		vehicle.reload()
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))

		self.assertIn("此車已記錄尾款", str(failure.exception))
		self.assertEqual(reservation.status, "有效")
		self.assertEqual(vehicle.status, "保留中")

	def _make_vehicle(self, **overrides):
		vehicle_data = {
			"doctype": "Used Car Vehicle",
			"brand": "Toyota",
			"model": "Altis",
			"year": 2020,
			"license_plate": f"TST-RES-{frappe.generate_hash(length=6)}",
			"vin": f"TST-RES-{frappe.generate_hash(length=10)}",
			"purchase_price": 300000,
		}
		vehicle_data.update(overrides)
		vehicle = frappe.get_doc(vehicle_data).insert()
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _make_stocked_vehicle(self):
		vehicle = self._make_vehicle()
		result = self.intake_service.complete_intake(vehicle.name)
		self._track_intake_result(result)
		vehicle.reload()
		return vehicle

	def _make_listed_vehicle(self):
		vehicle = self._make_stocked_vehicle()
		self.listing_service.list_vehicle(vehicle.name)
		vehicle.reload()
		return vehicle

	def _create_reservation(self, vehicle, **overrides):
		args = {
			"vehicle_name": vehicle.name,
			"customer_name": f"測試客戶{frappe.generate_hash(length=6)}",
			"customer_phone": f"09{frappe.generate_hash(length=8)}",
			"sold_price": 60000,
			"deposit_amount": 10000,
			"payment_method": "現金",
		}
		args.update(overrides)
		result = self.service.create_reservation(**args)
		if result.get("reservation"):
			self.created_reservations.append(result.get("reservation"))
		if result.get("customer"):
			self.created_customers.append(result.get("customer"))
		return result

	def _track_intake_result(self, result):
		if result.get("stock_entry"):
			self.created_stock_entries.append(result.get("stock_entry"))
		if result.get("serial_no"):
			self.created_serial_nos.append(result.get("serial_no"))
		if result.get("item"):
			self.created_items.append(result.get("item"))

	def _cleanup_linked_doc(self, doctype, name):
		if not name or not frappe.db.exists(doctype, name):
			return
		if doctype == "Journal Entry":
			doc = frappe.get_doc(doctype, name)
			if doc.docstatus == 1:
				doc.cancel()
			elif doc.docstatus == 0:
				frappe.delete_doc(doctype, name, force=True)
			return
		frappe.delete_doc(doctype, name, force=True)

	def _restricted_doc_counts(self):
		return {
			"Sales Invoice": frappe.db.count("Sales Invoice"),
			"Payment Entry": frappe.db.count("Payment Entry"),
			"Delivery Note": frappe.db.count("Delivery Note"),
			"Journal Entry": frappe.db.count("Journal Entry"),
		}
