import frappe
from frappe.utils import flt, nowdate

from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


RESTRICTED_ACCOUNTING_DOCTYPES = (
	"Stock Entry",
	"Purchase Invoice",
	"Sales Invoice",
	"Payment Entry",
	"Delivery Note",
	"Journal Entry",
)


class VehicleMoneyFlowService:
	def create_deposit_money_flow_from_reservation(self, reservation_name: str):
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.check_permission("read")
		self._validate_reservation_for_deposit_money_flow(reservation)

		money_flow = frappe.get_doc(
			{
				"doctype": "Used Car Money Flow",
				"flow_type": "訂金收款",
				"direction": "收入",
				"status": "待審核",
				"vehicle": reservation.vehicle,
				"reservation": reservation.name,
				"stock_no": reservation.stock_no,
				"customer": reservation.customer,
				"customer_name": reservation.customer_name,
				"customer_phone": reservation.customer_phone,
				"amount": reservation.deposit_amount,
				"payment_date": reservation.deposit_date,
				"payment_method": reservation.payment_method,
				"payment_reference": reservation.payment_reference,
				"notes": reservation.notes,
				"created_by_service": 1,
			}
		).insert()

		voucher_draft = VehicleVoucherService().create_deposit_voucher_draft(money_flow.name)
		money_flow.reload()
		reservation = frappe.get_doc("Used Car Reservation", reservation.name)
		reservation.flags.ignore_accounting_link_validation = True
		reservation.money_flow = money_flow.name
		reservation.voucher_draft = voucher_draft
		reservation.save()

		return {
			"money_flow": money_flow.name,
			"voucher_draft": voucher_draft,
			"amount": flt(money_flow.amount),
			"status": money_flow.status,
			"message": "已建立訂金金流紀錄與傳票草稿。",
		}

	def _validate_reservation_for_deposit_money_flow(self, reservation):
		if reservation.status != "有效":
			frappe.throw("只有有效保留紀錄可以建立訂金金流。")
		if flt(reservation.deposit_amount) <= 0:
			frappe.throw("訂金金額必須大於 0，才能建立金流紀錄。")
		if reservation.money_flow or reservation.voucher_draft:
			frappe.throw("此保留紀錄已建立金流紀錄。")


def verify_vehicle_money_flow_voucher_service():
	from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
	from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService
	from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService

	vehicle = None
	item_name = None
	stock_entry_name = None
	serial_no = None
	reservation_name = None
	money_flow_name = None
	voucher_draft_name = None
	journal_entry_name = None
	customer_name = None
	item_existed_before = False
	serial_existed_before = False
	customer_existed_before = False
	verification = {"cleaned_up": False}

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"VERIFY-MONEY-{frappe.generate_hash(length=4)}",
				"vin": f"VERIFY-MONEY-{frappe.generate_hash(length=10)}",
				"purchase_price": 300000,
			}
		).insert()
		stock_no = vehicle.stock_no
		item_existed_before = bool(frappe.db.exists("Item", stock_no))
		serial_existed_before = bool(frappe.db.exists("Serial No", vehicle.vin))
		customer_existed_before = bool(frappe.db.get_value("Customer", {"customer_name": "王小明"}, "name"))

		intake_result = VehicleIntakeService().complete_intake(vehicle.name)
		item_name = intake_result.get("item")
		stock_entry_name = intake_result.get("stock_entry")
		serial_no = intake_result.get("serial_no")
		VehicleListingService().list_vehicle(vehicle.name)

		before_counts = _money_flow_verification_doc_counts()

		reservation_result = VehicleReservationService().create_reservation(
			vehicle_name=vehicle.name,
			customer_name="王小明",
			customer_phone="0912345678",
			deposit_amount=10000,
			payment_method="現金",
			deposit_date=nowdate(),
			payment_reference="VERIFY",
		)
		reservation_name = reservation_result.get("reservation")
		money_flow_name = reservation_result.get("money_flow")
		voucher_draft_name = reservation_result.get("voucher_draft")
		customer_name = reservation_result.get("customer")

		vehicle.reload()
		money_flow = frappe.get_doc("Used Car Money Flow", money_flow_name)
		draft = frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)
		after_reservation_counts = _money_flow_verification_doc_counts()

		if vehicle.status != "保留中":
			frappe.throw("Money Flow verification did not update vehicle status to 保留中.")
		if money_flow.status != "待審核" or draft.status != "待審核":
			frappe.throw("Money Flow verification did not create pending money flow and voucher draft.")
		if draft.journal_entry:
			frappe.throw("Voucher draft must not have Journal Entry before confirm.")
		if flt(draft.total_debit) != flt(draft.total_credit) or flt(draft.difference) != 0:
			frappe.throw("Voucher draft lines are not balanced.")
		if after_reservation_counts["Journal Entry"] != before_counts["Journal Entry"]:
			frappe.throw("Reservation must not create Journal Entry before accounting confirm.")
		for doctype in ("Payment Entry", "Sales Invoice", "Delivery Note", "Stock Entry"):
			if after_reservation_counts[doctype] != before_counts[doctype]:
				frappe.throw(f"Reservation money flow must not create {doctype}.")

		confirm_result = VehicleVoucherService().confirm_voucher_draft(draft.name, "VERIFY CONFIRM")
		journal_entry_name = confirm_result.get("journal_entry")
		money_flow.reload()
		draft.reload()
		journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
		after_confirm_counts = _money_flow_verification_doc_counts()

		if draft.status != "已入帳" or money_flow.status != "已入帳":
			frappe.throw("Confirm voucher draft did not mark draft and money flow as posted.")
		if journal_entry.docstatus != 1:
			frappe.throw("Journal Entry was not submitted after confirm.")
		if after_confirm_counts["Journal Entry"] != before_counts["Journal Entry"] + 1:
			frappe.throw("Journal Entry count must increase only after confirm.")
		for doctype in ("Payment Entry", "Sales Invoice", "Delivery Note", "Stock Entry"):
			if after_confirm_counts[doctype] != after_reservation_counts[doctype]:
				frappe.throw(f"Confirm voucher draft must not create {doctype}.")

		verification = {
			"vehicle_name": vehicle.name,
			"stock_no": stock_no,
			"reservation": reservation_name,
			"money_flow": money_flow_name,
			"voucher_draft": voucher_draft_name,
			"journal_entry": journal_entry_name,
			"vehicle_status": vehicle.status,
			"money_flow_status": money_flow.status,
			"voucher_status": draft.status,
			"journal_entry_submitted": journal_entry.docstatus == 1,
			"journal_entry_created_only_after_confirm": after_confirm_counts["Journal Entry"] == before_counts["Journal Entry"] + 1,
			"payment_entry_count_unchanged": after_confirm_counts["Payment Entry"] == before_counts["Payment Entry"],
			"sales_invoice_count_unchanged": after_confirm_counts["Sales Invoice"] == before_counts["Sales Invoice"],
			"delivery_note_count_unchanged": after_confirm_counts["Delivery Note"] == before_counts["Delivery Note"],
			"stock_entry_count_unchanged_after_reservation": after_reservation_counts["Stock Entry"] == before_counts["Stock Entry"],
			"cleaned_up": False,
		}
	finally:
		try:
			stock_entry_cancelled = False
			if journal_entry_name and frappe.db.exists("Journal Entry", journal_entry_name):
				journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
				if journal_entry.docstatus == 1:
					journal_entry.cancel()
				elif journal_entry.docstatus == 0:
					frappe.delete_doc("Journal Entry", journal_entry_name, force=True)
			if voucher_draft_name and frappe.db.exists("Used Car Voucher Draft", voucher_draft_name):
				frappe.delete_doc("Used Car Voucher Draft", voucher_draft_name, force=True)
			if money_flow_name and frappe.db.exists("Used Car Money Flow", money_flow_name):
				frappe.delete_doc("Used Car Money Flow", money_flow_name, force=True)
			if reservation_name and frappe.db.exists("Used Car Reservation", reservation_name):
				frappe.delete_doc("Used Car Reservation", reservation_name, force=True)
			if stock_entry_name and frappe.db.exists("Stock Entry", stock_entry_name):
				stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
				if stock_entry.docstatus == 1:
					stock_entry.cancel()
					stock_entry_cancelled = True
				elif stock_entry.docstatus == 0:
					frappe.delete_doc("Stock Entry", stock_entry_name, force=True)
					stock_entry_cancelled = True
			if vehicle and frappe.db.exists("Used Car Vehicle", vehicle.name):
				frappe.db.set_value("Used Car Vehicle", vehicle.name, {"serial_no": None, "stock_entry": None, "item": None})
				frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
			if stock_entry_cancelled and not serial_existed_before and serial_no and frappe.db.exists("Serial No", serial_no):
				try:
					frappe.delete_doc("Serial No", serial_no, force=True)
				except Exception:
					# ERPNext 庫存歷史可能限制序號刪除，清理不得繞過標準保護。
					verification["serial_no_cleanup_skipped"] = True
			if stock_entry_cancelled and not item_existed_before and item_name and frappe.db.exists("Item", item_name):
				try:
					frappe.delete_doc("Item", item_name, force=True)
				except Exception:
					# Item 若已被庫存歷史引用，保留標準限制並回報。
					verification["item_cleanup_skipped"] = True
			if not customer_existed_before and customer_name and frappe.db.exists("Customer", customer_name):
				try:
					frappe.delete_doc("Customer", customer_name, force=True)
				except Exception:
					verification["customer_cleanup_skipped"] = True
			frappe.db.commit()
			verification["cleaned_up"] = True
		except Exception as exc:
			frappe.db.rollback()
			frappe.throw(f"Money Flow Voucher verification cleanup failed: {exc}")

	return verification


def _money_flow_verification_doc_counts():
	counts = {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
	counts["Used Car Money Flow"] = frappe.db.count("Used Car Money Flow")
	counts["Used Car Voucher Draft"] = frappe.db.count("Used Car Voucher Draft")
	return counts
