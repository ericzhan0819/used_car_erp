import frappe
from frappe.utils import flt, nowdate

from used_car_erp.used_car_erp.services.used_car_action_permission_service import assert_can_perform_used_car_action
from used_car_erp.used_car_erp.services.used_car_controlled_write_service import (
	insert_service_controlled_doc,
	save_service_controlled_doc,
)
from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


VALID_PAYMENT_METHODS = ("現金", "匯款", "信用卡", "其他")
GENERAL_EXPENSE_FLOW_TYPES = ("整備支出", "維修支出", "美容支出", "代辦支出", "拍場支出", "其他支出")
RESTRICTED_ACCOUNTING_DOCTYPES = (
	"Stock Entry",
	"Purchase Invoice",
	"Sales Invoice",
	"Payment Entry",
	"Delivery Note",
	"Journal Entry",
)


class VehicleMoneyFlowService:
	def create_general_expense_money_flow(
		self,
		vehicle: str,
		payment_date=None,
		flow_type: str | None = None,
		amount=0,
		payment_method: str | None = None,
		payment_reference: str | None = None,
		notes: str | None = None,
		evidence_attachment: str | None = None,
		cash_account: str | None = None,
		settlement_status: str | None = None,
		counterparty_name: str | None = None,
	):
		assert_can_perform_used_car_action(
			"used_car_money_flow.general_expense.create",
			message="你沒有建立中古車一般支出金流的權限。",
		)
		self._validate_general_expense_money_flow(vehicle, flow_type, amount, payment_method)
		vehicle_doc = frappe.get_doc("Used Car Vehicle", vehicle)
		vehicle_doc.check_permission("read")

		money_flow_values = {
			"doctype": "Used Car Money Flow",
			"flow_type": flow_type,
			"direction": "支出",
			"status": "待審核",
			"vehicle": vehicle_doc.name,
			"stock_no": vehicle_doc.stock_no,
			"amount": amount,
			"payment_date": payment_date or nowdate(),
			"payment_method": payment_method,
			"cash_account": cash_account or self._infer_cash_account_from_payment_method(payment_method),
			"settlement_status": settlement_status or self._default_settlement_status("支出"),
			"payment_reference": payment_reference,
			"counterparty_name": counterparty_name or payment_reference,
			"evidence_attachment": evidence_attachment,
			"notes": notes,
			"created_by_service": 1,
		}
		money_flow = insert_service_controlled_doc(
			frappe.get_doc(money_flow_values),
			action="used_car_money_flow.general_expense.create",
			allowed_doctype="Used Car Money Flow",
			fieldnames=money_flow_values.keys(),
		)

		voucher_draft = VehicleVoucherService().create_general_expense_voucher_draft_from_money_flow_service(money_flow.name)
		money_flow.reload()

		return {
			"money_flow": money_flow.name,
			"voucher_draft": voucher_draft,
			"amount": flt(money_flow.amount),
			"status": money_flow.status,
			"message": "已建立一般支出金流紀錄與傳票草稿。",
		}

	def create_deposit_money_flow_from_reservation(self, reservation_name: str):
		assert_can_perform_used_car_action(
			"used_car_money_flow.deposit.create",
			message="你沒有建立中古車訂金金流的權限。",
		)
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.check_permission("read")
		self._validate_reservation_for_deposit_money_flow(reservation)

		money_flow_values = {
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
			"cash_account": self._infer_cash_account_from_payment_method(reservation.payment_method),
			"settlement_status": self._default_settlement_status("收入"),
			"payment_reference": reservation.payment_reference,
			"counterparty_name": reservation.customer_name,
			"notes": reservation.notes,
			"created_by_service": 1,
		}
		money_flow = insert_service_controlled_doc(
			frappe.get_doc(money_flow_values),
			action="used_car_money_flow.deposit.create",
			allowed_doctype="Used Car Money Flow",
			fieldnames=money_flow_values.keys(),
		)

		voucher_draft = VehicleVoucherService().create_deposit_voucher_draft_from_money_flow_service(money_flow.name)
		money_flow.reload()
		reservation = frappe.get_doc("Used Car Reservation", reservation.name)
		reservation.flags.ignore_accounting_link_validation = True
		save_service_controlled_doc(
			reservation,
			action="used_car_money_flow.deposit.create",
			allowed_doctype="Used Car Reservation",
			values={"money_flow": money_flow.name, "voucher_draft": voucher_draft},
		)

		return {
			"money_flow": money_flow.name,
			"voucher_draft": voucher_draft,
			"amount": flt(money_flow.amount),
			"status": money_flow.status,
			"message": "已建立訂金金流紀錄與傳票草稿。",
		}

	def create_final_payment_money_flow_from_reservation(
		self,
		reservation_name: str,
		amount,
		payment_method: str,
		payment_date=None,
		payment_reference: str | None = None,
		notes: str | None = None,
		cash_account: str | None = None,
		settlement_status: str | None = None,
		counterparty_name: str | None = None,
	):
		assert_can_perform_used_car_action(
			"used_car_money_flow.final_payment.create",
			message="你沒有建立中古車尾款金流的權限。",
		)
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.check_permission("read")
		deposit_money_flow, deposit_voucher_draft = self._validate_reservation_for_final_payment_money_flow(reservation, amount, payment_method)

		money_flow_values = {
			"doctype": "Used Car Money Flow",
			"flow_type": "尾款收款",
			"direction": "收入",
			"status": "待審核",
			"vehicle": reservation.vehicle,
			"reservation": reservation.name,
			"stock_no": reservation.stock_no,
			"customer": reservation.customer,
			"customer_name": reservation.customer_name,
			"customer_phone": reservation.customer_phone,
			"amount": amount,
			"payment_date": payment_date or nowdate(),
			"payment_method": payment_method,
			"cash_account": cash_account or self._infer_cash_account_from_payment_method(payment_method),
			"settlement_status": settlement_status or self._default_settlement_status("收入"),
			"payment_reference": payment_reference,
			"counterparty_name": counterparty_name or reservation.customer_name,
			"notes": notes,
			"created_by_service": 1,
		}
		money_flow = insert_service_controlled_doc(
			frappe.get_doc(money_flow_values),
			action="used_car_money_flow.final_payment.create",
			allowed_doctype="Used Car Money Flow",
			fieldnames=money_flow_values.keys(),
		)

		voucher_draft = VehicleVoucherService().create_final_payment_voucher_draft_from_money_flow_service(money_flow.name)
		money_flow.reload()
		reservation = frappe.get_doc("Used Car Reservation", reservation.name)
		reservation.flags.ignore_accounting_link_validation = True
		reservation_updates = {
			"final_payment_amount": amount,
			"final_payment_date": money_flow.payment_date,
			"final_payment_method": payment_method,
			"final_payment_reference": payment_reference,
			"final_payment_notes": notes,
			"final_money_flow": money_flow.name,
			"final_voucher_draft": voucher_draft,
		}
		if not reservation.money_flow:
			reservation_updates["money_flow"] = deposit_money_flow
		if not reservation.voucher_draft:
			reservation_updates["voucher_draft"] = deposit_voucher_draft
		save_service_controlled_doc(
			reservation,
			action="used_car_money_flow.final_payment.create",
			allowed_doctype="Used Car Reservation",
			values=reservation_updates,
		)

		return {
			"reservation": reservation.name,
			"money_flow": money_flow.name,
			"voucher_draft": voucher_draft,
			"amount": flt(money_flow.amount),
			"status": money_flow.status,
			"message": "已建立尾款金流紀錄與傳票草稿。",
		}

	def create_deposit_refund_money_flow_from_reservation(
		self,
		reservation_name: str,
		refund_payment_method: str,
		refund_date=None,
		refund_reference: str | None = None,
		refund_notes: str | None = None,
	):
		assert_can_perform_used_car_action(
			"used_car_money_flow.deposit_refund.create",
			message="你沒有建立中古車訂金退款的權限。",
		)
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.check_permission("read")
		self._validate_reservation_for_deposit_refund_money_flow(reservation, refund_payment_method)

		money_flow_values = {
			"doctype": "Used Car Money Flow",
			"flow_type": "退款",
			"direction": "支出",
			"status": "待審核",
			"vehicle": reservation.vehicle,
			"reservation": reservation.name,
			"stock_no": reservation.stock_no,
			"customer": reservation.customer,
			"customer_name": reservation.customer_name,
			"customer_phone": reservation.customer_phone,
			"amount": reservation.deposit_amount,
			"payment_date": refund_date or nowdate(),
			"payment_method": refund_payment_method,
			"cash_account": self._infer_cash_account_from_payment_method(refund_payment_method),
			"settlement_status": self._default_settlement_status("支出"),
			"payment_reference": refund_reference,
			"counterparty_name": reservation.customer_name,
			"notes": refund_notes,
			"created_by_service": 1,
		}
		money_flow = insert_service_controlled_doc(
			frappe.get_doc(money_flow_values),
			action="used_car_money_flow.deposit_refund.create",
			allowed_doctype="Used Car Money Flow",
			fieldnames=money_flow_values.keys(),
		)

		voucher_draft = VehicleVoucherService().create_deposit_refund_voucher_draft_from_money_flow_service(money_flow.name)
		money_flow.reload()

		return {
			"reservation": reservation.name,
			"money_flow": money_flow.name,
			"voucher_draft": voucher_draft,
			"amount": flt(money_flow.amount),
			"status": money_flow.status,
			"message": "已建立訂金退款待處理資料。",
		}

	def _validate_reservation_for_deposit_money_flow(self, reservation):
		if reservation.status != "有效":
			frappe.throw("只有有效保留紀錄可以建立訂金金流。")
		if flt(reservation.deposit_amount) <= 0:
			frappe.throw("訂金金額必須大於 0，才能建立金流紀錄。")
		if reservation.money_flow or reservation.voucher_draft:
			frappe.throw("此保留紀錄已建立金流紀錄。")

	def _validate_general_expense_money_flow(self, vehicle, flow_type: str | None, amount, payment_method: str | None):
		if not vehicle:
			frappe.throw("車輛為必填。")
		if flow_type not in GENERAL_EXPENSE_FLOW_TYPES:
			frappe.throw("一般支出類型必須是：整備支出、維修支出、美容支出、代辦支出、拍場支出、其他支出。")
		if flt(amount) <= 0:
			frappe.throw("一般支出金額必須大於 0。")
		if payment_method not in VALID_PAYMENT_METHODS:
			frappe.throw("付款方式必須是：現金、匯款、信用卡、其他。")

	def _validate_reservation_for_final_payment_money_flow(self, reservation, amount, payment_method: str):
		if reservation.status != "有效":
			frappe.throw("只有有效保留紀錄可以建立尾款金流。")
		deposit_money_flow = self._resolve_deposit_money_flow(reservation)
		deposit_voucher_draft = self._resolve_deposit_voucher_draft(reservation, deposit_money_flow)
		if not deposit_money_flow or not deposit_voucher_draft:
			frappe.throw("此保留紀錄尚未建立訂金金流與傳票草稿，不可建立尾款。")
		if reservation.final_money_flow or reservation.final_voucher_draft:
			frappe.throw("此保留紀錄已建立尾款金流紀錄。")
		if flt(amount) <= 0:
			frappe.throw("尾款金額必須大於 0。")
		if payment_method not in VALID_PAYMENT_METHODS:
			frappe.throw("付款方式必須是：現金、匯款、信用卡、其他。")

		vehicle = frappe.get_doc("Used Car Vehicle", reservation.vehicle)
		vehicle.check_permission("read")
		if vehicle.status != "保留中":
			frappe.throw("只有保留中車輛可以建立尾款金流。")

		if frappe.db.exists("Used Car Money Flow", {"reservation": reservation.name, "flow_type": "尾款收款", "status": ["!=", "已作廢"]}):
			frappe.throw("此保留紀錄已有未作廢的尾款金流紀錄。")
		return deposit_money_flow, deposit_voucher_draft

	def _validate_reservation_for_deposit_refund_money_flow(self, reservation, payment_method: str):
		if reservation.status != "有效":
			frappe.throw("只有有效保留紀錄可以建立訂金退款。")
		if flt(reservation.deposit_amount) <= 0:
			frappe.throw("訂金金額必須大於 0，才能建立訂金退款。")
		if payment_method not in VALID_PAYMENT_METHODS:
			frappe.throw("退款方式必須是：現金、匯款、信用卡、其他。")
		if frappe.db.exists("Used Car Money Flow", {"reservation": reservation.name, "flow_type": "退款", "status": ["!=", "已作廢"]}):
			frappe.throw("此保留紀錄已有未作廢的退款資料。")

	def _infer_cash_account_from_payment_method(self, payment_method: str | None):
		account_by_payment_method = {
			"現金": "現金",
			"匯款": "主要銀行",
			"其他": "其他",
			"信用卡": "其他",
		}
		account_name = account_by_payment_method.get(payment_method)
		if not account_name:
			return None
		return frappe.db.get_value(
			"Used Car Cash Account",
			{"account_name": account_name, "is_active": 1},
			"name",
		)

	def _default_settlement_status(self, direction: str | None):
		if direction == "收入":
			return "已收款"
		if direction == "支出":
			return "已付款"
		return None

	def _resolve_deposit_money_flow(self, reservation):
		if reservation.money_flow and frappe.db.exists("Used Car Money Flow", reservation.money_flow):
			return reservation.money_flow
		return frappe.db.get_value(
			"Used Car Money Flow",
			{"reservation": reservation.name, "flow_type": "訂金收款", "status": ["!=", "已作廢"]},
			"name",
			order_by="creation desc",
		)

	def _resolve_deposit_voucher_draft(self, reservation, money_flow_name):
		if reservation.voucher_draft and frappe.db.exists("Used Car Voucher Draft", reservation.voucher_draft):
			return reservation.voucher_draft
		if money_flow_name:
			voucher_draft = frappe.db.get_value(
				"Used Car Voucher Draft",
				{"money_flow": money_flow_name, "status": ["!=", "已作廢"]},
				"name",
				order_by="creation desc",
			)
			if voucher_draft:
				return voucher_draft
		return frappe.db.get_value(
			"Used Car Voucher Draft",
			{"reservation": reservation.name, "status": ["!=", "已作廢"]},
			"name",
			order_by="creation desc",
		)


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
			sold_price=60000,
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
		cleanup_errors = verification.setdefault("cleanup_errors", [])
		stock_entry_cancelled = False
		_safe_cleanup_journal_entry(journal_entry_name, verification)
		_safe_clear_accounting_links(
			vehicle.name if vehicle else None,
			reservation_name,
			money_flow_name,
			voucher_draft_name,
			journal_entry_name,
			verification,
		)
		verification["voucher_draft_deleted"] = _safe_delete_voucher_draft(voucher_draft_name, verification)
		verification["money_flow_deleted"] = _safe_delete_money_flow(money_flow_name, verification)
		verification["reservation_deleted"] = _safe_delete_reservation(reservation_name, verification)
		try:
			if stock_entry_name and frappe.db.exists("Stock Entry", stock_entry_name):
				stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
				if stock_entry.docstatus == 1:
					stock_entry.cancel()
					stock_entry_cancelled = True
				elif stock_entry.docstatus == 0:
					frappe.delete_doc("Stock Entry", stock_entry_name, force=True, ignore_permissions=True)
					stock_entry_cancelled = True
		except Exception as exc:
			cleanup_errors.append(f"stock_entry_cleanup_error: {exc}")
		try:
			if vehicle and frappe.db.exists("Used Car Vehicle", vehicle.name):
				frappe.db.set_value("Used Car Vehicle", vehicle.name, {"serial_no": None, "stock_entry": None, "item": None})
				frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True, ignore_permissions=True)
		except Exception as exc:
			cleanup_errors.append(f"vehicle_cleanup_error: {exc}")
		verification["vehicle_deleted"] = not vehicle or not frappe.db.exists("Used Car Vehicle", vehicle.name)
		if stock_entry_cancelled and not serial_existed_before and serial_no and frappe.db.exists("Serial No", serial_no):
			try:
				frappe.delete_doc("Serial No", serial_no, force=True, ignore_permissions=True)
			except Exception:
				# ERPNext 庫存歷史可能限制序號刪除，清理不得繞過標準保護。
				verification["serial_no_cleanup_skipped"] = True
		if stock_entry_cancelled and not item_existed_before and item_name and frappe.db.exists("Item", item_name):
			try:
				frappe.delete_doc("Item", item_name, force=True, ignore_permissions=True)
			except Exception:
				# Item 若已被庫存歷史引用，保留標準限制並回報。
				verification["item_cleanup_skipped"] = True
		if not customer_existed_before and customer_name and frappe.db.exists("Customer", customer_name):
			try:
				frappe.delete_doc("Customer", customer_name, force=True, ignore_permissions=True)
			except Exception:
				verification["customer_cleanup_skipped"] = True
		verification["cleaned_up"] = _money_flow_verification_cleanup_complete(
			voucher_draft_name,
			money_flow_name,
			reservation_name,
			vehicle.name if vehicle else None,
			cleanup_errors,
		)
		frappe.db.commit()

	return verification


def _money_flow_verification_doc_counts():
	counts = {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
	counts["Used Car Money Flow"] = frappe.db.count("Used Car Money Flow")
	counts["Used Car Voucher Draft"] = frappe.db.count("Used Car Voucher Draft")
	return counts


def _safe_cleanup_journal_entry(journal_entry_name, verification):
	if not journal_entry_name or not frappe.db.exists("Journal Entry", journal_entry_name):
		return
	try:
		journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
		if journal_entry.docstatus == 1:
			journal_entry.cancel()
		elif journal_entry.docstatus == 0:
			frappe.delete_doc("Journal Entry", journal_entry_name, force=True, ignore_permissions=True)
	except Exception as exc:
		verification.setdefault("cleanup_errors", []).append(f"journal_entry_cleanup_error: {exc}")


def _safe_clear_accounting_links(vehicle_name, reservation_name, money_flow_name, voucher_draft_name, journal_entry_name, verification):
	try:
		_safe_clear_doc_links("Used Car Money Flow", money_flow_name, ("voucher_draft", "journal_entry"))
		_safe_clear_doc_links(
			"Used Car Reservation",
			reservation_name,
			(
				"money_flow",
				"voucher_draft",
				"journal_entry",
				"final_money_flow",
				"final_voucher_draft",
				"final_journal_entry",
			),
		)
		_safe_clear_doc_links("Used Car Vehicle", vehicle_name, ("money_flow", "voucher_draft", "reservation", "journal_entry"))
		if voucher_draft_name and frappe.db.exists("Used Car Voucher Draft", voucher_draft_name):
			# 驗證工具只清自己建立的草稿；正式傳票若仍存在，避免硬刪造成會計資料風險。
			draft_journal_entry = frappe.db.get_value("Used Car Voucher Draft", voucher_draft_name, "journal_entry")
			if draft_journal_entry and draft_journal_entry != journal_entry_name and frappe.db.exists("Journal Entry", draft_journal_entry):
				verification.setdefault("cleanup_errors", []).append("voucher_draft_cleanup_skipped: linked to unexpected Journal Entry")
			else:
				_safe_clear_doc_links("Used Car Voucher Draft", voucher_draft_name, ("journal_entry",))
	except Exception as exc:
		verification.setdefault("cleanup_errors", []).append(f"clear_accounting_links_error: {exc}")


def _safe_clear_doc_links(doctype, name, fields):
	if not name or not frappe.db.exists(doctype, name):
		return
	meta = frappe.get_meta(doctype)
	values = {field: None for field in fields if meta.has_field(field)}
	if values:
		frappe.db.set_value(doctype, name, values)


def _safe_delete_voucher_draft(voucher_draft_name, verification):
	if not voucher_draft_name or not frappe.db.exists("Used Car Voucher Draft", voucher_draft_name):
		return True
	try:
		frappe.delete_doc("Used Car Voucher Draft", voucher_draft_name, force=True, ignore_permissions=True)
	except Exception as exc:
		verification.setdefault("cleanup_errors", []).append(f"voucher_draft_cleanup_error: {exc}")
	return not frappe.db.exists("Used Car Voucher Draft", voucher_draft_name)


def _safe_delete_money_flow(money_flow_name, verification):
	if not money_flow_name or not frappe.db.exists("Used Car Money Flow", money_flow_name):
		return True
	try:
		frappe.delete_doc("Used Car Money Flow", money_flow_name, force=True, ignore_permissions=True)
	except Exception as exc:
		verification.setdefault("cleanup_errors", []).append(f"money_flow_cleanup_error: {exc}")
	return not frappe.db.exists("Used Car Money Flow", money_flow_name)


def _safe_delete_reservation(reservation_name, verification):
	if not reservation_name or not frappe.db.exists("Used Car Reservation", reservation_name):
		return True
	try:
		frappe.delete_doc("Used Car Reservation", reservation_name, force=True, ignore_permissions=True)
	except Exception as exc:
		verification.setdefault("cleanup_errors", []).append(f"reservation_cleanup_error: {exc}")
	return not frappe.db.exists("Used Car Reservation", reservation_name)


def _money_flow_verification_cleanup_complete(voucher_draft_name, money_flow_name, reservation_name, vehicle_name, cleanup_errors):
	return not cleanup_errors and all(
		not name or not frappe.db.exists(doctype, name)
		for doctype, name in (
			("Used Car Voucher Draft", voucher_draft_name),
			("Used Car Money Flow", money_flow_name),
			("Used Car Reservation", reservation_name),
			("Used Car Vehicle", vehicle_name),
		)
	)


@frappe.whitelist()
def create_general_expense_money_flow(
	vehicle: str,
	payment_date=None,
	flow_type: str | None = None,
	amount=0,
	payment_method: str | None = None,
	payment_reference: str | None = None,
	notes: str | None = None,
	evidence_attachment: str | None = None,
	cash_account: str | None = None,
	settlement_status: str | None = None,
	counterparty_name: str | None = None,
):
	service = VehicleMoneyFlowService()
	return service.create_general_expense_money_flow(
		vehicle=vehicle,
		payment_date=payment_date,
		flow_type=flow_type,
		amount=amount,
		payment_method=payment_method,
		payment_reference=payment_reference,
		notes=notes,
		evidence_attachment=evidence_attachment,
		cash_account=cash_account,
		settlement_status=settlement_status,
		counterparty_name=counterparty_name,
	)


@frappe.whitelist()
def create_final_payment_money_flow_from_reservation(
	reservation_name: str,
	amount,
	payment_method: str,
	payment_date=None,
	payment_reference: str | None = None,
	notes: str | None = None,
	cash_account: str | None = None,
	settlement_status: str | None = None,
	counterparty_name: str | None = None,
):
	service = VehicleMoneyFlowService()
	return service.create_final_payment_money_flow_from_reservation(
		reservation_name=reservation_name,
		amount=amount,
		payment_method=payment_method,
		payment_date=payment_date,
		payment_reference=payment_reference,
		notes=notes,
		cash_account=cash_account,
		settlement_status=settlement_status,
		counterparty_name=counterparty_name,
	)
