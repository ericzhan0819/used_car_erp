import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.used_car_action_permission_service import (
	ACTION_ROLE_MAP,
	UsedCarActionPermissionError,
	assert_can_perform_used_car_action,
	is_action_allowed_for_roles,
)


class TestUsedCarActionPermissionService(FrappeTestCase):
	def test_sales_can_create_reservation(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_reservation.create", {"Used Car Sales"}))

	def test_sales_can_create_deposit_money_flow(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_money_flow.deposit.create", {"Used Car Sales"}))

	def test_sales_can_cancel_with_deposit_handling(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_reservation.cancel_with_deposit_handling", {"Used Car Sales"}))

	def test_deposit_refund_create_is_known_action(self):
		self.assertIn("used_car_money_flow.deposit_refund.create", ACTION_ROLE_MAP)
		self.assertTrue(is_action_allowed_for_roles("used_car_money_flow.deposit_refund.create", {"Used Car Sales"}))

	def test_general_expense_money_flow_create_is_known_action(self):
		self.assertIn("used_car_money_flow.general_expense.create", ACTION_ROLE_MAP)
		self.assertTrue(is_action_allowed_for_roles("used_car_money_flow.general_expense.create", {"Used Car Sales"}))

	def test_purchase_payment_money_flow_create_is_known_action(self):
		self.assertIn("used_car_money_flow.purchase_payment.create", ACTION_ROLE_MAP)
		self.assertTrue(is_action_allowed_for_roles("used_car_money_flow.purchase_payment.create", {"Used Car Sales"}))

	def test_purchase_payment_money_flow_create_still_requires_allowed_role(self):
		self.assertFalse(is_action_allowed_for_roles("used_car_money_flow.purchase_payment.create", {"Used Car Accounting"}))

	def test_general_expense_money_flow_create_still_requires_allowed_role(self):
		self.assertFalse(is_action_allowed_for_roles("used_car_money_flow.general_expense.create", {"Used Car Accounting"}))

	def test_sales_cannot_confirm_voucher_draft(self):
		self.assertFalse(is_action_allowed_for_roles("used_car_voucher_draft.confirm", {"Used Car Sales"}))

	def test_accounting_can_confirm_voucher_draft(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_voucher_draft.confirm", {"Used Car Accounting"}))

	def test_accounting_can_reject_voucher_draft(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_voucher_draft.reject", {"Used Car Accounting"}))

	def test_accounting_can_void_voucher_draft(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_voucher_draft.void", {"Used Car Accounting"}))

	def test_accounting_cannot_create_reservation(self):
		self.assertFalse(is_action_allowed_for_roles("used_car_reservation.create", {"Used Car Accounting"}))

	def test_preparation_can_create_vehicle_cost_with_amount(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_vehicle_cost.create_with_amount", {"Used Car Preparation"}))

	def test_preparation_cannot_write_vehicle_cost_amount(self):
		self.assertFalse(is_action_allowed_for_roles("used_car_vehicle_cost.amount.write", {"Used Car Preparation"}))

	def test_accounting_manager_can_write_vehicle_cost_amount(self):
		self.assertTrue(is_action_allowed_for_roles("used_car_vehicle_cost.amount.write", {"Used Car Accounting Manager"}))

	def test_owner_can_create_and_complete_reservation_but_cannot_confirm_voucher(self):
		owner_roles = {"Used Car Owner"}

		self.assertTrue(is_action_allowed_for_roles("used_car_reservation.create", owner_roles))
		self.assertTrue(is_action_allowed_for_roles("used_car_reservation.complete_sale", owner_roles))
		self.assertFalse(is_action_allowed_for_roles("used_car_voucher_draft.confirm", owner_roles))

	def test_owner_with_accounting_role_can_confirm_voucher(self):
		roles = {"Used Car Owner", "Used Car Accounting"}

		self.assertTrue(is_action_allowed_for_roles("used_car_voucher_draft.confirm", roles))

	def test_system_manager_can_perform_all_known_actions(self):
		for action in ACTION_ROLE_MAP:
			with self.subTest(action=action):
				self.assertTrue(is_action_allowed_for_roles(action, {"System Manager"}))

	def test_unknown_action_is_not_allowed_and_assert_raises(self):
		self.assertFalse(is_action_allowed_for_roles("used_car.unknown", {"System Manager"}))

		with self.assertRaises(UsedCarActionPermissionError):
			assert_can_perform_used_car_action("used_car.unknown", user="Administrator")

	def test_empty_roles_are_not_allowed(self):
		self.assertFalse(is_action_allowed_for_roles("used_car_reservation.create", []))
		self.assertFalse(is_action_allowed_for_roles("used_car_reservation.create", None))
