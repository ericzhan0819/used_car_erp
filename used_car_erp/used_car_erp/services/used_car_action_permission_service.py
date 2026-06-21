import frappe


SYSTEM_BYPASS_ROLES = {"System Manager"}

ACTION_ROLE_MAP = {
	"used_car_vehicle.intake.complete": {
		"Used Car Procurement",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_vehicle.purchase_price.write": {
		"Used Car Procurement",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_vehicle.status.transition": {
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_reservation.create": {
		"Used Car Sales",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_reservation.cancel": {
		"Used Car Sales",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_reservation.complete_sale": {
		"Used Car Sales",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_money_flow.deposit.create": {
		"Used Car Sales",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_money_flow.final_payment.create": {
		"Used Car Sales",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_money_flow.general_expense.create": {
		"Used Car Sales",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_vehicle_cost.create_with_amount": {
		"Used Car Preparation",
		"Used Car Accounting Manager",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_vehicle_cost.amount.write": {
		"Used Car Accounting Manager",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_vehicle_cost.summary.recalculate": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
		"Used Car Manager",
		"Used Car Owner",
	},
	"used_car_voucher_draft.create": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_voucher_draft.confirm": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_voucher_draft.reject": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_voucher_draft.void": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_sales_invoice_draft.create": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_sales_invoice.submit": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_formal_delivery.status.sync": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_formal_delivery.advance_settlement.link": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_advance_settlement.create_draft": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_advance_settlement.submit": {
		"Used Car Accounting",
		"Used Car Accounting Manager",
	},
	"used_car_tax_metadata.write": {
		"Used Car Accounting Manager",
	},
	"used_car_accounting_link.repair": {
		"Used Car Accounting Manager",
	},
}


class UsedCarActionPermissionError(frappe.PermissionError):
	pass


def get_action_roles(action: str) -> set[str]:
	"""Return allowed business roles for a used-car action.

	Unknown action raises UsedCarActionPermissionError so new business actions cannot
	be accidentally allowed without an explicit action map decision.
	"""
	roles = ACTION_ROLE_MAP.get(action)
	if roles is None:
		frappe.throw(
			f"未知的中古車操作權限：{action}",
			exc=UsedCarActionPermissionError,
		)
	return set(roles)


def is_action_allowed_for_roles(action: str, roles) -> bool:
	"""Pure role-set check for tests.

	Unknown action returns False here to keep role-map tests lightweight. Runtime
	assertion still raises through get_action_roles/assert_can_perform_used_car_action.
	"""
	try:
		allowed_roles = get_action_roles(action)
	except UsedCarActionPermissionError:
		return False

	role_set = set(roles or [])
	if not role_set:
		return False
	if role_set.intersection(SYSTEM_BYPASS_ROLES):
		return True
	return bool(role_set.intersection(allowed_roles))


def can_perform_used_car_action(action: str, user: str | None = None) -> bool:
	"""Runtime check against frappe.get_roles(user)."""
	user = user or getattr(frappe.session, "user", None)
	if not user or user == "Guest":
		return False
	return is_action_allowed_for_roles(action, frappe.get_roles(user))


def assert_can_perform_used_car_action(
	action: str,
	user: str | None = None,
	message: str | None = None,
) -> None:
	"""Raise PermissionError if user lacks action permission.

	Message is intentionally user-facing Chinese because this helper will be called
	from whitelisted service actions after P1-F-2 adoption.
	"""
	get_action_roles(action)
	if can_perform_used_car_action(action, user=user):
		return

	frappe.throw(
		message or f"你沒有執行此中古車業務操作的權限：{action}",
		exc=UsedCarActionPermissionError,
	)
