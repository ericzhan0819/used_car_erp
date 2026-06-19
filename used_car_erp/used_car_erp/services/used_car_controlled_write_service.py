import frappe

from used_car_erp.used_car_erp.services.used_car_action_permission_service import (
	assert_can_perform_used_car_action,
)


CONTROLLED_WRITE_ALLOWED_FIELDS = {
	"used_car_reservation.create": {
		"Used Car Reservation": {
			"doctype",
			"vehicle",
			"stock_no",
			"vehicle_title",
			"customer",
			"customer_name",
			"customer_phone",
			"deposit_amount",
			"deposit_date",
			"payment_method",
			"payment_reference",
			"notes",
			"status",
			"created_by_service",
		},
		"Used Car Vehicle": {"status"},
	},
	"used_car_money_flow.deposit.create": {
		"Used Car Money Flow": {
			"doctype",
			"flow_type",
			"direction",
			"status",
			"vehicle",
			"reservation",
			"stock_no",
			"customer",
			"customer_name",
			"customer_phone",
			"amount",
			"payment_date",
			"payment_method",
			"payment_reference",
			"notes",
			"created_by_service",
			"voucher_draft",
		},
		"Used Car Voucher Draft": {
			"doctype",
			"status",
			"posting_date",
			"money_flow",
			"vehicle",
			"reservation",
			"customer",
			"memo",
			"review_note",
			"lines",
		},
		"Used Car Reservation": {"money_flow", "voucher_draft"},
	},
	"used_car_money_flow.final_payment.create": {
		"Used Car Money Flow": {
			"doctype",
			"flow_type",
			"direction",
			"status",
			"vehicle",
			"reservation",
			"stock_no",
			"customer",
			"customer_name",
			"customer_phone",
			"amount",
			"payment_date",
			"payment_method",
			"payment_reference",
			"notes",
			"created_by_service",
			"voucher_draft",
		},
		"Used Car Voucher Draft": {
			"doctype",
			"status",
			"posting_date",
			"money_flow",
			"vehicle",
			"reservation",
			"customer",
			"memo",
			"review_note",
			"lines",
		},
		"Used Car Reservation": {
			"money_flow",
			"voucher_draft",
			"final_payment_amount",
			"final_payment_date",
			"final_payment_method",
			"final_payment_reference",
			"final_payment_notes",
			"final_money_flow",
			"final_voucher_draft",
		},
	},
	"used_car_reservation.cancel": {
		"Used Car Reservation": {"status", "cancellation_reason", "cancelled_at", "cancelled_by"},
		"Used Car Vehicle": {"status"},
	},
	"used_car_reservation.complete_sale": {
		"Used Car Vehicle": {
			"status",
			"completed_reservation",
			"completed_at",
			"completed_by",
			"completion_note",
			"deposit_money_flow",
			"deposit_voucher_draft",
			"deposit_journal_entry",
			"final_money_flow",
			"final_voucher_draft",
			"final_journal_entry",
		},
		"Used Car Reservation": {"status", "completed_at", "completed_by", "completion_note"},
	},
	"used_car_formal_delivery.status.sync": {
		"Used Car Vehicle": {
			"formal_delivery_status",
			"formal_delivery_completed_at",
			"formal_delivery_completed_by",
			"formal_delivery_note",
			"formal_delivery_posting_date",
		},
	},
}


class UsedCarControlledWriteError(frappe.PermissionError):
	pass


def get_controlled_write_allowed_fields(action: str, doctype: str) -> set[str]:
	"""Return allowed fields for action + doctype.

	Unknown action or disallowed doctype raises UsedCarControlledWriteError so
	service-owned bypass cannot silently expand to unrelated documents.
	"""
	action_policy = CONTROLLED_WRITE_ALLOWED_FIELDS.get(action)
	if action_policy is None:
		frappe.throw(f"未知的中古車 controlled write 操作：{action}", exc=UsedCarControlledWriteError)

	allowed_fields = action_policy.get(doctype)
	if allowed_fields is None:
		frappe.throw(
			f"此中古車服務操作不可寫入文件類型：{doctype}",
			exc=UsedCarControlledWriteError,
		)
	return set(allowed_fields)


def assert_controlled_write_policy(action: str, doctype: str, fieldnames) -> None:
	"""Pure policy check for tests."""
	allowed_fields = get_controlled_write_allowed_fields(action, doctype)
	written_fields = set(fieldnames or [])
	disallowed_fields = written_fields - allowed_fields
	if disallowed_fields:
		frappe.throw(
			f"此中古車服務操作不可寫入未授權欄位：{', '.join(sorted(disallowed_fields))}",
			exc=UsedCarControlledWriteError,
		)


def insert_service_controlled_doc(doc, *, action: str, allowed_doctype: str, fieldnames) -> object:
	"""Insert a doc with ignore_permissions=True only after action gate and field policy pass."""
	assert_can_perform_used_car_action(action)
	if doc.doctype != allowed_doctype:
		frappe.throw(
			f"此中古車服務操作不可建立文件類型：{doc.doctype}",
			exc=UsedCarControlledWriteError,
		)
	assert_controlled_write_policy(action, allowed_doctype, fieldnames)
	return doc.insert(ignore_permissions=True)


def save_service_controlled_doc(doc, *, action: str, allowed_doctype: str, values: dict) -> object:
	"""Set whitelisted values and save with ignore_permissions=True after action gate and field policy pass."""
	assert_can_perform_used_car_action(action)
	if doc.doctype != allowed_doctype:
		frappe.throw(
			f"此中古車服務操作不可儲存文件類型：{doc.doctype}",
			exc=UsedCarControlledWriteError,
		)
	assert_controlled_write_policy(action, allowed_doctype, values.keys())
	for fieldname, value in values.items():
		doc.set(fieldname, value)
	return doc.save(ignore_permissions=True)


def db_set_service_controlled_values(
	doctype: str,
	name: str,
	*,
	action: str,
	values: dict,
	update_modified: bool = True,
) -> None:
	"""Use frappe.db.set_value only after action gate and field policy pass."""
	assert_can_perform_used_car_action(action)
	assert_controlled_write_policy(action, doctype, values.keys())
	frappe.db.set_value(doctype, name, values, update_modified=update_modified)
