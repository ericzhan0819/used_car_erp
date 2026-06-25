from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.used_car_controlled_write_service import (
	UsedCarControlledWriteError,
	assert_controlled_write_policy,
)


class TestUsedCarControlledWriteService(FrappeTestCase):
	def test_reservation_create_allows_reservation_fields(self):
		assert_controlled_write_policy(
			"used_car_reservation.create",
			"Used Car Reservation",
			{"doctype", "vehicle", "deposit_amount", "created_by_service"},
		)

	def test_reservation_create_allows_vehicle_sale_summary_fields(self):
		assert_controlled_write_policy(
			"used_car_reservation.create",
			"Used Car Vehicle",
			{"status", "customer", "sold_price", "reserved_date", "sales_staff", "sales_note"},
		)

	def test_reservation_create_rejects_unapproved_reservation_field(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car_reservation.create", "Used Car Reservation", {"journal_entry"})

	def test_reservation_create_rejects_voucher_draft_doctype(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car_reservation.create", "Used Car Voucher Draft", {"doctype"})

	def test_deposit_money_flow_allows_voucher_draft_link(self):
		assert_controlled_write_policy(
			"used_car_money_flow.deposit.create",
			"Used Car Money Flow",
			{"voucher_draft"},
		)

	def test_money_flow_create_actions_allow_cash_account_fields(self):
		cash_account_fields = {"cash_account", "settlement_status", "counterparty_name"}
		for action in (
			"used_car_money_flow.general_expense.create",
			"used_car_money_flow.deposit.create",
			"used_car_money_flow.final_payment.create",
			"used_car_money_flow.deposit_refund.create",
		):
			assert_controlled_write_policy(action, "Used Car Money Flow", cash_account_fields)

	def test_money_flow_create_actions_reject_unapproved_money_flow_field(self):
		for action in (
			"used_car_money_flow.general_expense.create",
			"used_car_money_flow.deposit.create",
			"used_car_money_flow.final_payment.create",
			"used_car_money_flow.deposit_refund.create",
		):
			with self.assertRaises(UsedCarControlledWriteError):
				assert_controlled_write_policy(action, "Used Car Money Flow", {"unauthorized_field"})

	def test_deposit_money_flow_allows_voucher_draft_lines(self):
		assert_controlled_write_policy(
			"used_car_money_flow.deposit.create",
			"Used Car Voucher Draft",
			{"doctype", "lines"},
		)

	def test_deposit_money_flow_rejects_vehicle_purchase_price(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car_money_flow.deposit.create", "Used Car Vehicle", {"purchase_price"})

	def test_final_payment_allows_reservation_final_links(self):
		assert_controlled_write_policy(
			"used_car_money_flow.final_payment.create",
			"Used Car Reservation",
			{"final_money_flow", "final_voucher_draft"},
		)

	def test_general_expense_money_flow_allows_money_flow_and_voucher_draft_fields(self):
		assert_controlled_write_policy(
			"used_car_money_flow.general_expense.create",
			"Used Car Money Flow",
			{"doctype", "flow_type", "direction", "vehicle", "evidence_attachment", "voucher_draft"},
		)
		assert_controlled_write_policy(
			"used_car_money_flow.general_expense.create",
			"Used Car Voucher Draft",
			{"doctype", "money_flow", "vehicle", "lines"},
		)

	def test_general_expense_money_flow_rejects_unapproved_doctype(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy(
				"used_car_money_flow.general_expense.create",
				"Used Car Vehicle",
				{"status"},
			)

	def test_cancel_allows_reservation_cancellation_fields(self):
		assert_controlled_write_policy(
			"used_car_reservation.cancel",
			"Used Car Reservation",
			{"status", "cancellation_reason", "cancelled_at", "cancelled_by"},
		)

	def test_cancel_rejects_final_payment_amount(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car_reservation.cancel", "Used Car Reservation", {"final_payment_amount"})

	def test_cancel_with_deposit_handling_allows_only_cancellation_and_void_fields(self):
		assert_controlled_write_policy(
			"used_car_reservation.cancel_with_deposit_handling",
			"Used Car Reservation",
			{"status", "cancellation_reason", "cancelled_at", "cancelled_by"},
		)
		assert_controlled_write_policy(
			"used_car_reservation.cancel_with_deposit_handling",
			"Used Car Vehicle",
			{"status", "customer", "sold_price", "reserved_date", "sales_staff", "sales_note"},
		)
		assert_controlled_write_policy("used_car_reservation.cancel_with_deposit_handling", "Used Car Money Flow", {"status"})
		assert_controlled_write_policy(
			"used_car_reservation.cancel_with_deposit_handling",
			"Used Car Voucher Draft",
			{"status", "reviewed_by", "reviewed_at", "review_note"},
		)

	def test_deposit_refund_create_allows_money_flow_and_voucher_draft_fields(self):
		assert_controlled_write_policy(
			"used_car_money_flow.deposit_refund.create",
			"Used Car Money Flow",
			{"doctype", "flow_type", "direction", "status", "reservation", "voucher_draft"},
		)
		assert_controlled_write_policy(
			"used_car_money_flow.deposit_refund.create",
			"Used Car Voucher Draft",
			{"doctype", "posting_date", "money_flow", "reservation", "lines"},
		)
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car_money_flow.deposit_refund.create", "Journal Entry", {"doctype"})

	def test_complete_sale_allows_vehicle_completion_summary_fields(self):
		assert_controlled_write_policy(
			"used_car_reservation.complete_sale",
			"Used Car Vehicle",
			{"status", "sold_date", "completed_reservation", "deposit_money_flow", "final_voucher_draft"},
		)

	def test_unknown_action_raises(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car.unknown", "Used Car Reservation", {"status"})

	def test_disallowed_doctype_raises(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car_reservation.cancel", "Used Car Money Flow", {"status"})

	def test_disallowed_field_raises(self):
		with self.assertRaises(UsedCarControlledWriteError):
			assert_controlled_write_policy("used_car_reservation.complete_sale", "Used Car Vehicle", {"purchase_price"})
