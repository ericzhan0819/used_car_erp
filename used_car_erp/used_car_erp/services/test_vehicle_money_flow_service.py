import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services import vehicle_money_flow_service
from used_car_erp.used_car_erp.doctype.used_car_money_flow.used_car_money_flow import UsedCarMoneyFlow
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
		self.created_sales_invoices = []
		self.created_customers = []

	def tearDown(self):
		for reservation_name in reversed(self.created_reservations):
			if frappe.db.exists("Used Car Reservation", reservation_name):
				updates = {}
				meta = frappe.get_meta("Used Car Reservation")
				for fieldname in (
					"status",
					"money_flow",
					"voucher_draft",
					"journal_entry",
					"final_money_flow",
					"final_voucher_draft",
					"final_journal_entry",
					"completed_at",
					"completed_by",
					"completion_note",
				):
					if meta.has_field(fieldname):
						updates[fieldname] = "有效" if fieldname == "status" else None
				if updates:
					frappe.db.set_value("Used Car Reservation", reservation_name, updates)
		for journal_entry_name in reversed(self.created_journal_entries):
			if frappe.db.exists("Journal Entry", journal_entry_name):
				journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
				if journal_entry.docstatus == 1:
					journal_entry.cancel()
				elif journal_entry.docstatus == 0:
					frappe.delete_doc("Journal Entry", journal_entry_name, force=True)
		for sales_invoice_name in reversed(self.created_sales_invoices):
			if frappe.db.exists("Sales Invoice", sales_invoice_name):
				sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
				if sales_invoice.docstatus == 1:
					sales_invoice.cancel()
				elif sales_invoice.docstatus == 0:
					frappe.delete_doc("Sales Invoice", sales_invoice_name, force=True)
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
				frappe.db.set_value(
					"Used Car Vehicle",
					vehicle_name,
					{
						"status": "草稿",
						"serial_no": None,
						"stock_entry": None,
						"item": None,
						"completed_reservation": None,
						"completed_at": None,
						"completed_by": None,
						"completion_note": None,
						"deposit_money_flow": None,
						"deposit_voucher_draft": None,
						"deposit_journal_entry": None,
						"final_money_flow": None,
						"final_voucher_draft": None,
						"final_journal_entry": None,
						"sales_invoice": None,
						"formal_delivery_status": "未處理",
						"formal_delivery_posting_date": None,
						"advance_settlement_journal_entry": None,
						"formal_delivery_completed_at": None,
						"formal_delivery_completed_by": None,
						"formal_delivery_note": None,
					},
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

	def test_create_reservation_creates_money_flow(self):
		result = self._create_reservation_for_listed_vehicle()
		self.assertTrue(frappe.db.exists("Used Car Money Flow", result.get("money_flow")))

	def test_vehicle_tax_metadata_fields_exist(self):
		meta = frappe.get_meta("Used Car Vehicle")
		for fieldname in (
			"purchase_source_type",
			"vehicle_tax_mode",
			"purchase_document_type",
			"purchase_document_no",
			"purchase_price",
			"tax_review_status",
			"tax_review_note",
		):
			self.assertTrue(meta.has_field(fieldname), fieldname)

	def test_vehicle_tax_metadata_defaults(self):
		vehicle = self._make_vehicle()

		self.assertEqual(vehicle.purchase_source_type, "個人")
		self.assertEqual(vehicle.vehicle_tax_mode, "待確認")
		self.assertEqual(vehicle.purchase_document_type, "未取得")
		self.assertEqual(vehicle.tax_review_status, "待確認")

	def test_vehicle_purchase_price_cannot_be_negative(self):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"TST-MF-{frappe.generate_hash(length=6)}",
				"vin": f"TST-MF-{frappe.generate_hash(length=10)}",
				"purchase_price": -1,
			}
		)

		with self.assertRaises(frappe.ValidationError) as failure:
			vehicle.insert()
		self.assertIn("買入金額不可為負數。", str(failure.exception))

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

	def test_create_general_expense_creates_money_flow_and_voucher_draft(self):
		vehicle = self._make_listed_vehicle()
		result = self._create_general_expense_for_vehicle(vehicle.name)
		money_flow = frappe.get_doc("Used Car Money Flow", result.get("money_flow"))
		draft = frappe.get_doc("Used Car Voucher Draft", result.get("voucher_draft"))

		self.assertEqual(money_flow.vehicle, vehicle.name)
		self.assertEqual(money_flow.direction, "支出")
		self.assertEqual(money_flow.flow_type, "維修支出")
		self.assertEqual(money_flow.evidence_attachment, "/files/test-expense.pdf")
		self.assertEqual(money_flow.voucher_draft, draft.name)
		self.assertEqual(draft.money_flow, money_flow.name)
		self.assertEqual(draft.vehicle, vehicle.name)
		self.assertEqual(draft.status, "待審核")
		self.assertEqual(result.get("status"), "待審核")

	def test_create_general_expense_uses_controlled_write(self):
		calls = []

		class FakeVehicle:
			name = "UC-TEST-001"
			stock_no = "STOCK-001"

			def check_permission(self, permission_type):
				self.permission_type = permission_type

		class FakeMoneyFlow:
			doctype = "Used Car Money Flow"
			name = "MF-TEST-001"
			amount = 1200
			status = "待審核"

			def reload(self):
				pass

		class FakeVoucherService:
			def create_general_expense_voucher_draft_from_money_flow_service(self, money_flow_name):
				return "VD-TEST-001"

		def fake_get_doc(*args):
			if args == ("Used Car Vehicle", "UC-TEST-001"):
				return FakeVehicle()
			if len(args) == 1 and args[0].get("doctype") == "Used Car Money Flow":
				return FakeMoneyFlow()
			raise AssertionError(args)

		def fake_insert_service_controlled_doc(doc, *, action, allowed_doctype, fieldnames):
			calls.append(
				{
					"action": action,
					"allowed_doctype": allowed_doctype,
					"fieldnames": set(fieldnames),
				}
			)
			return doc

		original_get_doc = vehicle_money_flow_service.frappe.get_doc
		original_insert = vehicle_money_flow_service.insert_service_controlled_doc
		original_voucher_service = vehicle_money_flow_service.VehicleVoucherService
		try:
			vehicle_money_flow_service.frappe.get_doc = fake_get_doc
			vehicle_money_flow_service.insert_service_controlled_doc = fake_insert_service_controlled_doc
			vehicle_money_flow_service.VehicleVoucherService = FakeVoucherService

			result = self.money_flow_service.create_general_expense_money_flow(
				vehicle="UC-TEST-001",
				payment_date="2026-06-12",
				flow_type="整備支出",
				amount=1200,
				payment_method="現金",
				payment_reference="TEST EXPENSE",
				evidence_attachment="/files/test-expense.pdf",
			)
		finally:
			vehicle_money_flow_service.frappe.get_doc = original_get_doc
			vehicle_money_flow_service.insert_service_controlled_doc = original_insert
			vehicle_money_flow_service.VehicleVoucherService = original_voucher_service

		self.assertEqual(result.get("money_flow"), "MF-TEST-001")
		self.assertEqual(calls[0]["action"], "used_car_money_flow.general_expense.create")
		self.assertEqual(calls[0]["allowed_doctype"], "Used Car Money Flow")
		self.assertIn("evidence_attachment", calls[0]["fieldnames"])

	def test_money_flow_validation_accepts_general_expense_flow_type(self):
		money_flow = UsedCarMoneyFlow(
			{
				"doctype": "Used Car Money Flow",
				"status": "待審核",
				"flow_type": "整備支出",
				"vehicle": "UC-TEST-001",
				"payment_date": "2026-06-12",
				"payment_method": "現金",
				"amount": 1200,
			}
		)

		money_flow.validate()

	def test_money_flow_validation_rejects_unknown_flow_type(self):
		money_flow = UsedCarMoneyFlow(
			{
				"doctype": "Used Car Money Flow",
				"status": "待審核",
				"flow_type": "未知支出",
				"vehicle": "UC-TEST-001",
				"payment_date": "2026-06-12",
				"payment_method": "現金",
				"amount": 1200,
			}
		)

		with self.assertRaises(frappe.ValidationError) as failure:
			money_flow.validate()
		self.assertIn("金流類型必須是", str(failure.exception))

	def test_create_general_expense_rejects_non_positive_amount(self):
		vehicle = self._make_listed_vehicle()

		with self.assertRaises(frappe.ValidationError) as failure:
			self.money_flow_service.create_general_expense_money_flow(
				vehicle=vehicle.name,
				flow_type="維修支出",
				amount=0,
				payment_method="現金",
			)
		self.assertIn("一般支出金額必須大於 0", str(failure.exception))

	def test_create_general_expense_rejects_non_expense_flow_type(self):
		vehicle = self._make_listed_vehicle()

		with self.assertRaises(frappe.ValidationError) as failure:
			self.money_flow_service.create_general_expense_money_flow(
				vehicle=vehicle.name,
				flow_type="訂金收款",
				amount=1000,
				payment_method="現金",
			)
		self.assertIn("一般支出類型必須是", str(failure.exception))

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

		self.assertEqual(after_counts["Journal Entry"], before_counts["Journal Entry"])
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

	def test_complete_reservation_rejects_missing_final_payment(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST DEPOSIT CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")
		self.assertIn("尚未建立尾款金流紀錄", str(failure.exception))

	def test_complete_reservation_rejects_unposted_final_payment(self):
		result = self._create_reservation_for_listed_vehicle()
		confirm_result = self.voucher_service.confirm_voucher_draft(result.get("voucher_draft"), "TEST DEPOSIT CONFIRM")
		self.created_journal_entries.append(confirm_result.get("journal_entry"))
		self._create_final_payment_for_reservation(result.get("reservation"))

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")
		self.assertIn("尾款金流尚未入帳", str(failure.exception))

	def test_complete_reservation_passes_after_deposit_and_final_posted(self):
		result = self._create_fully_posted_reservation()
		complete_result = self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")
		vehicle = frappe.get_doc("Used Car Vehicle", result.get("vehicle_name"))
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))

		self.assertEqual(complete_result.get("vehicle_status"), "已售出")
		self.assertEqual(complete_result.get("reservation_status"), "已完成")
		self.assertEqual(vehicle.status, "已售出")
		self.assertEqual(reservation.status, "已完成")
		self.assertTrue(reservation.completed_at)
		self.assertTrue(reservation.completed_by)

	def test_complete_reservation_writes_vehicle_completion_summary(self):
		result = self._create_fully_posted_reservation()
		self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")
		vehicle = frappe.get_doc("Used Car Vehicle", result.get("vehicle_name"))

		self.assertEqual(vehicle.completed_reservation, result.get("reservation"))
		self.assertTrue(vehicle.completed_at)
		self.assertTrue(vehicle.completed_by)
		self.assertEqual(vehicle.completion_note, "TEST COMPLETE")
		self.assertEqual(vehicle.deposit_money_flow, result.get("money_flow"))
		self.assertEqual(vehicle.deposit_voucher_draft, result.get("voucher_draft"))
		self.assertEqual(vehicle.deposit_journal_entry, result.get("deposit_journal_entry"))
		self.assertEqual(vehicle.final_money_flow, result.get("final_money_flow"))
		self.assertEqual(vehicle.final_voucher_draft, result.get("final_voucher_draft"))
		self.assertEqual(vehicle.final_journal_entry, result.get("final_journal_entry"))

	def test_complete_reservation_does_not_create_restricted_documents(self):
		result = self._create_fully_posted_reservation()
		before_counts = self._restricted_doc_counts()
		self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")
		after_counts = self._restricted_doc_counts()

		self.assertEqual(after_counts["Journal Entry"], before_counts["Journal Entry"])
		self.assertEqual(after_counts["Payment Entry"], before_counts["Payment Entry"])
		self.assertEqual(after_counts["Sales Invoice"], before_counts["Sales Invoice"])
		self.assertEqual(after_counts["Delivery Note"], before_counts["Delivery Note"])
		self.assertEqual(after_counts["Stock Entry"], before_counts["Stock Entry"])

	def test_completed_reservation_cannot_complete_again(self):
		result = self._create_fully_posted_reservation()
		self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST AGAIN")
		self.assertIn("車輛狀態不是保留中", str(failure.exception))

	def test_sold_vehicle_cannot_complete_again(self):
		result = self._create_fully_posted_reservation()
		frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), "status", "已售出")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")
		self.assertIn("車輛狀態不是保留中", str(failure.exception))

	def test_sold_vehicle_cannot_create_reservation(self):
		vehicle = self._make_listed_vehicle()
		frappe.db.set_value("Used Car Vehicle", vehicle.name, "status", "已售出")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.create_reservation(
				vehicle_name=vehicle.name,
				customer_name=f"測試客戶{frappe.generate_hash(length=6)}",
				customer_phone=f"09{frappe.generate_hash(length=8)}",
				deposit_amount=10000,
				payment_method="現金",
			)
		self.assertIn("只有上架中車輛可以建立訂金保留", str(failure.exception))

	def test_completed_reservation_cannot_be_cancelled(self):
		result = self._create_fully_posted_reservation()
		self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.cancel_reservation(result.get("reservation"), "TEST CANCEL")
		self.assertIn("只有有效的保留可以取消", str(failure.exception))

	def test_completed_reservation_cannot_create_final_payment(self):
		result = self._create_fully_posted_reservation()
		self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.money_flow_service.create_final_payment_money_flow_from_reservation(
				result.get("reservation"),
				50000,
				"現金",
			)
		self.assertIn("只有有效保留紀錄可以建立尾款金流", str(failure.exception))

	def test_formal_delivery_preflight_rejects_before_completion(self):
		result = self._create_fully_posted_reservation()

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
		self.assertIn("車輛狀態不是已售出", str(failure.exception))

	def test_formal_delivery_preflight_passes_after_completion(self):
		result = self._create_completed_reservation()
		preflight = self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))

		self.assertTrue(preflight.get("passed"))
		self.assertEqual(preflight.get("reservation"), result.get("reservation"))
		self.assertEqual(preflight.get("customer"), result.get("customer"))
		self.assertEqual(preflight.get("item"), result.get("item"))
		self.assertEqual(preflight.get("serial_no"), result.get("serial_no"))
		self.assertEqual(preflight.get("sales_amount"), 60000)

	def test_formal_delivery_preflight_backfills_missing_completed_reservation(self):
		result = self._create_completed_reservation()
		frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), "completed_reservation", None)

		preflight = self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
		vehicle = frappe.get_doc("Used Car Vehicle", result.get("vehicle_name"))

		self.assertTrue(preflight.get("passed"))
		self.assertEqual(vehicle.completed_reservation, result.get("reservation"))

	def test_formal_delivery_preflight_rejects_uncompleted_reservation(self):
		result = self._create_completed_reservation()
		frappe.db.set_value("Used Car Reservation", result.get("reservation"), "status", "有效")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
		self.assertIn("保留單狀態不是已完成", str(failure.exception))

	def test_formal_delivery_preflight_rejects_missing_deposit_links(self):
		missing_link_cases = (
			("deposit_money_flow", "缺少訂金金流紀錄"),
			("deposit_voucher_draft", "缺少訂金傳票草稿"),
			("deposit_journal_entry", "缺少訂金正式會計傳票"),
		)
		for fieldname, message in missing_link_cases:
			with self.subTest(fieldname=fieldname):
				result = self._create_completed_reservation()
				frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), fieldname, None)

				with self.assertRaises(frappe.ValidationError) as failure:
					self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
				self.assertIn(message, str(failure.exception))

	def test_formal_delivery_preflight_rejects_missing_final_links(self):
		missing_link_cases = (
			("final_money_flow", "缺少尾款金流紀錄"),
			("final_voucher_draft", "缺少尾款傳票草稿"),
			("final_journal_entry", "缺少尾款正式會計傳票"),
		)
		for fieldname, message in missing_link_cases:
			with self.subTest(fieldname=fieldname):
				result = self._create_completed_reservation()
				frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), fieldname, None)

				with self.assertRaises(frappe.ValidationError) as failure:
					self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
				self.assertIn(message, str(failure.exception))

	def test_formal_delivery_preflight_rejects_missing_item(self):
		result = self._create_completed_reservation()
		frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), "item", None)

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
		self.assertIn("車輛尚未建立 Item", str(failure.exception))

	def test_formal_delivery_preflight_rejects_missing_serial_no(self):
		result = self._create_completed_reservation()
		frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), "serial_no", None)

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
		self.assertIn("車輛尚未建立 Serial No", str(failure.exception))

	def test_formal_delivery_preflight_does_not_create_restricted_documents(self):
		result = self._create_completed_reservation()
		before_counts = self._restricted_doc_counts()
		self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
		after_counts = self._restricted_doc_counts()

		self.assertEqual(after_counts["Sales Invoice"], before_counts["Sales Invoice"])
		self.assertEqual(after_counts["Payment Entry"], before_counts["Payment Entry"])
		self.assertEqual(after_counts["Delivery Note"], before_counts["Delivery Note"])
		self.assertEqual(after_counts["Stock Entry"], before_counts["Stock Entry"])
		self.assertEqual(after_counts["Journal Entry"], before_counts["Journal Entry"])
		self.assertEqual(after_counts["Purchase Invoice"], before_counts["Purchase Invoice"])

	def test_formal_delivery_preflight_keeps_vehicle_and_reservation_status(self):
		result = self._create_completed_reservation()
		self.reservation_service.preflight_formal_delivery_for_vehicle(result.get("vehicle_name"))
		vehicle = frappe.get_doc("Used Car Vehicle", result.get("vehicle_name"))
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))

		self.assertEqual(vehicle.status, "已售出")
		self.assertEqual(reservation.status, "已完成")

	def test_create_sales_invoice_draft_rejects_failed_preflight(self):
		result = self._create_fully_posted_reservation()
		before_count = frappe.db.count("Sales Invoice")

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.create_sales_invoice_draft_for_vehicle(result.get("vehicle_name"))

		self.assertIn("車輛狀態不是已售出", str(failure.exception))
		self.assertEqual(frappe.db.count("Sales Invoice"), before_count)

	def test_create_sales_invoice_draft_after_formal_delivery_preflight(self):
		result = self._create_completed_reservation()
		before_counts = self._restricted_doc_counts()
		draft_result = self.reservation_service.create_sales_invoice_draft_for_vehicle(
			result.get("vehicle_name"),
			posting_date="2026-06-12",
			note="TEST DRAFT",
		)
		self.created_sales_invoices.append(draft_result.get("sales_invoice"))
		after_counts = self._restricted_doc_counts()
		sales_invoice = frappe.get_doc("Sales Invoice", draft_result.get("sales_invoice"))
		vehicle = frappe.get_doc("Used Car Vehicle", result.get("vehicle_name"))
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))

		self.assertEqual(after_counts["Sales Invoice"], before_counts["Sales Invoice"] + 1)
		self.assertEqual(after_counts["Payment Entry"], before_counts["Payment Entry"])
		self.assertEqual(after_counts["Delivery Note"], before_counts["Delivery Note"])
		self.assertEqual(after_counts["Stock Entry"], before_counts["Stock Entry"])
		self.assertEqual(after_counts["Journal Entry"], before_counts["Journal Entry"])
		self.assertEqual(after_counts["Purchase Invoice"], before_counts["Purchase Invoice"])
		self.assertEqual(sales_invoice.docstatus, 0)
		self.assertTrue(sales_invoice.company)
		self.assertEqual(sales_invoice.customer, reservation.customer)
		self.assertEqual(str(sales_invoice.posting_date), "2026-06-12")
		self.assertEqual(sales_invoice.update_stock, 1)
		self.assertEqual(sales_invoice.items[0].item_code, vehicle.item)
		self.assertEqual(sales_invoice.items[0].qty, 1)
		self.assertIn(vehicle.serial_no, sales_invoice.items[0].serial_no)
		self.assertEqual(sales_invoice.items[0].rate, 60000)
		self.assertTrue(sales_invoice.items[0].income_account)
		income_account = frappe.get_doc("Account", sales_invoice.items[0].income_account)
		self.assertEqual(income_account.company, sales_invoice.company)
		self.assertEqual(income_account.is_group, 0)
		self.assertEqual(vehicle.sales_invoice, sales_invoice.name)
		self.assertEqual(vehicle.formal_delivery_status, "銷售發票草稿")
		self.assertEqual(str(vehicle.formal_delivery_posting_date), "2026-06-12")
		self.assertEqual(vehicle.formal_delivery_note, "TEST DRAFT")
		self.assertFalse(vehicle.advance_settlement_journal_entry)
		self.assertFalse(vehicle.formal_delivery_completed_at)
		self.assertFalse(vehicle.formal_delivery_completed_by)
		self.assertEqual(vehicle.status, "已售出")
		self.assertEqual(reservation.status, "已完成")
		self.assertEqual(draft_result.get("sales_invoice_status"), "Draft")

	def test_duplicate_sales_invoice_draft_is_rejected(self):
		result = self._create_completed_reservation()
		draft_result = self.reservation_service.create_sales_invoice_draft_for_vehicle(result.get("vehicle_name"))
		self.created_sales_invoices.append(draft_result.get("sales_invoice"))

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.create_sales_invoice_draft_for_vehicle(result.get("vehicle_name"))

		self.assertIn("已建立 Sales Invoice", str(failure.exception))

	def test_manual_formal_delivery_field_change_is_rejected_but_service_flag_allowed(self):
		vehicle = self._make_listed_vehicle()
		vehicle.formal_delivery_status = "銷售發票草稿"
		self.assertRaises(frappe.ValidationError, vehicle.save)

		vehicle = frappe.get_doc("Used Car Vehicle", vehicle.name)
		vehicle.flags.ignore_formal_delivery_validation = True
		vehicle.formal_delivery_status = "銷售發票草稿"
		vehicle.save()
		vehicle.reload()
		self.assertEqual(vehicle.formal_delivery_status, "銷售發票草稿")

	def test_create_sales_invoice_draft_rejects_missing_warehouse(self):
		result = self._create_completed_reservation()
		frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), "stock_warehouse", None)
		frappe.db.set_value("Used Car Vehicle", result.get("vehicle_name"), "stock_entry", None)

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service.create_sales_invoice_draft_for_vehicle(result.get("vehicle_name"))

		self.assertIn("找不到車輛庫存倉", str(failure.exception))

	def test_resolve_sales_income_account_rejects_missing_income_account(self):
		vehicle = self._make_listed_vehicle()

		with self.assertRaises(frappe.ValidationError) as failure:
			self.reservation_service._resolve_sales_income_account(vehicle.item, "TEST MISSING COMPANY")

		self.assertIn("找不到公司 TEST MISSING COMPANY，無法建立 Sales Invoice 草稿。", str(failure.exception))

	def test_resolve_sales_income_account_allows_empty_item_defaults(self):
		vehicle = self._make_listed_vehicle()
		company = self.reservation_service._resolve_company_for_sales_invoice(vehicle)
		item = frappe.get_doc("Item", vehicle.item)
		item_group = frappe.get_doc("Item Group", item.item_group)
		item.item_defaults = None
		item_group.item_defaults = None

		income_account = self.reservation_service._resolve_sales_income_account(vehicle.item, company)

		self.assertTrue(income_account)

	def test_manual_reservation_status_change_is_rejected(self):
		result = self._create_reservation_for_listed_vehicle()
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))
		reservation.status = "已完成"

		self.assertRaises(frappe.ValidationError, reservation.save)

	def test_manual_completion_field_change_is_rejected_but_service_flag_allowed(self):
		result = self._create_reservation_for_listed_vehicle()
		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))
		reservation.completion_note = "MANUAL"
		self.assertRaises(frappe.ValidationError, reservation.save)

		reservation = frappe.get_doc("Used Car Reservation", result.get("reservation"))
		reservation.flags.ignore_accounting_link_validation = True
		reservation.completion_note = "SERVICE"
		reservation.save()
		reservation.reload()
		self.assertEqual(reservation.completion_note, "SERVICE")

	def test_manual_vehicle_completion_summary_change_is_rejected_but_service_flag_allowed(self):
		vehicle = self._make_listed_vehicle()
		vehicle.completed_at = frappe.utils.now()
		self.assertRaises(frappe.ValidationError, vehicle.save)

		vehicle = frappe.get_doc("Used Car Vehicle", vehicle.name)
		vehicle.flags.ignore_sale_completion_validation = True
		vehicle.completed_at = frappe.utils.now()
		vehicle.save()
		vehicle.reload()
		self.assertTrue(vehicle.completed_at)

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

	def _create_general_expense_for_vehicle(self, vehicle_name):
		result = self.money_flow_service.create_general_expense_money_flow(
			vehicle=vehicle_name,
			payment_date="2026-06-12",
			flow_type="維修支出",
			amount=1200,
			payment_method="現金",
			payment_reference="TEST EXPENSE",
			notes="TEST NOTE",
			evidence_attachment="/files/test-expense.pdf",
		)
		self.created_money_flows.append(result.get("money_flow"))
		self.created_voucher_drafts.append(result.get("voucher_draft"))
		return result

	def _create_fully_posted_reservation(self):
		result = self._create_reservation_for_listed_vehicle()
		vehicle = frappe.get_doc("Used Car Vehicle", result.get("vehicle_name"))
		result.update({"item": vehicle.item, "serial_no": vehicle.serial_no})
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

	def _create_completed_reservation(self):
		result = self._create_fully_posted_reservation()
		self.reservation_service.complete_active_reservation(result.get("vehicle_name"), "TEST COMPLETE")
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
			"Journal Entry": frappe.db.count("Journal Entry"),
			"Stock Entry": frappe.db.count("Stock Entry"),
			"Purchase Invoice": frappe.db.count("Purchase Invoice"),
			"Payment Entry": frappe.db.count("Payment Entry"),
			"Sales Invoice": frappe.db.count("Sales Invoice"),
			"Delivery Note": frappe.db.count("Delivery Note"),
		}
