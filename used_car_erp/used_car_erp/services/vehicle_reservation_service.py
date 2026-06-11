import frappe
from frappe.utils import flt, now, nowdate

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService
from used_car_erp.used_car_erp.services.vehicle_money_flow_service import VehicleMoneyFlowService


VALID_PAYMENT_METHODS = ("現金", "匯款", "信用卡", "其他")
RESTRICTED_ACCOUNTING_DOCTYPES = (
	"Stock Entry",
	"Purchase Invoice",
	"Sales Invoice",
	"Payment Entry",
	"Delivery Note",
	"Journal Entry",
)


class VehicleReservationService:
	def create_reservation(
		self,
		vehicle_name: str,
		customer_name: str,
		customer_phone: str,
		deposit_amount,
		payment_method: str,
		deposit_date=None,
		payment_reference: str | None = None,
		notes: str | None = None,
		customer: str | None = None,
	):
		self._validate_customer_inputs(customer_name, customer_phone)
		self._validate_deposit_amount(deposit_amount)
		self._validate_payment_method(payment_method)

		try:
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
			vehicle.check_permission("write")
			self._validate_vehicle_ready_for_reservation(vehicle)
			self._validate_no_active_reservation(vehicle.name)

			resolved_customer = customer or self._resolve_or_create_customer(customer_name, customer_phone)
			if not frappe.db.exists("Customer", resolved_customer):
				frappe.throw("指定的 ERPNext 客戶不存在。")

			previous_status = vehicle.status
			reservation = frappe.get_doc(
				{
					"doctype": "Used Car Reservation",
					"vehicle": vehicle.name,
					"stock_no": vehicle.stock_no,
					"vehicle_title": self._vehicle_title(vehicle),
					"customer": resolved_customer,
					"customer_name": customer_name,
					"customer_phone": customer_phone,
					"deposit_amount": deposit_amount,
					"deposit_date": deposit_date or nowdate(),
					"payment_method": payment_method,
					"payment_reference": payment_reference,
					"notes": notes,
					"status": "有效",
					"created_by_service": 1,
				}
			).insert()

			money_flow_result = VehicleMoneyFlowService().create_deposit_money_flow_from_reservation(reservation.name)

			# 訂金保留只切換中古車業務狀態；正式會計傳票必須由傳票草稿人工確認後才建立。
			frappe.db.set_value("Used Car Vehicle", vehicle.name, "status", "保留中")
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"reservation": reservation.name,
			"money_flow": money_flow_result.get("money_flow"),
			"voucher_draft": money_flow_result.get("voucher_draft"),
			"vehicle_name": vehicle.name,
			"stock_no": vehicle.stock_no,
			"previous_status": previous_status,
			"status": "保留中",
			"customer": resolved_customer,
			"customer_name": customer_name,
			"customer_phone": customer_phone,
			"deposit_amount": flt(deposit_amount),
			"payment_method": payment_method,
			"changed": True,
			"message": "已建立訂金保留、金流紀錄與傳票草稿，車輛已改為保留中。",
		}

	def cancel_reservation(self, reservation_name: str, reason: str):
		if not reason:
			frappe.throw("取消原因為必填。")

		try:
			reservation = frappe.get_doc("Used Car Reservation", reservation_name)
			reservation.check_permission("write")
			if reservation.status != "有效":
				frappe.throw("只有有效的保留可以取消。")

			vehicle = frappe.get_doc("Used Car Vehicle", reservation.vehicle)
			vehicle.check_permission("write")
			previous_status = vehicle.status

			# 取消資訊由 service 寫入，避免使用者直接改狀態造成保留與車輛狀態不一致。
			reservation.status = "已取消"
			reservation.cancellation_reason = reason
			reservation.cancelled_at = now()
			reservation.cancelled_by = frappe.session.user
			reservation.save()

			if vehicle.status == "保留中":
				frappe.db.set_value("Used Car Vehicle", vehicle.name, "status", "上架中")
				status = "上架中"
			else:
				status = vehicle.status

			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"reservation": reservation.name,
			"vehicle_name": vehicle.name,
			"previous_status": previous_status,
			"status": status,
			"reservation_status": "已取消",
			"changed": True,
			"message": "已取消保留，車輛已回到上架中。",
		}

	def cancel_active_reservation_for_vehicle(self, vehicle_name: str, reason: str):
		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle_name, "status": "有效"},
			"name",
			order_by="creation desc",
		)
		if not reservation_name:
			frappe.throw("找不到此車輛的有效保留紀錄。")

		return self.cancel_reservation(reservation_name, reason)

	def get_active_reservation_for_vehicle(self, vehicle_name: str):
		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle_name, "status": "有效"},
			"name",
			order_by="creation desc",
		)
		if not reservation_name:
			return None

		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.check_permission("read")
		return {
			"reservation": reservation.name,
			"customer": reservation.customer,
			"customer_name": reservation.customer_name,
			"customer_phone": reservation.customer_phone,
			"deposit_amount": reservation.deposit_amount,
			"payment_method": reservation.payment_method,
			"deposit_date": reservation.deposit_date,
		}

	def _validate_vehicle_ready_for_reservation(self, vehicle):
		if not vehicle.item or not vehicle.serial_no or not vehicle.stock_entry:
			frappe.throw("車輛必須完成入庫後，才能建立訂金保留。")
		if vehicle.status != "上架中":
			frappe.throw("只有上架中車輛可以建立訂金保留。")

	def _validate_no_active_reservation(self, vehicle_name: str):
		if frappe.db.exists("Used Car Reservation", {"vehicle": vehicle_name, "status": "有效"}):
			frappe.throw("此車輛已有有效保留紀錄，不可重複建立。")

	def _validate_customer_inputs(self, customer_name: str, customer_phone: str):
		if not customer_name:
			frappe.throw("客戶姓名為必填。")
		if not customer_phone:
			frappe.throw("客戶電話為必填。")

	def _validate_deposit_amount(self, deposit_amount):
		if flt(deposit_amount) <= 0:
			frappe.throw("訂金金額必須大於 0。")

	def _validate_payment_method(self, payment_method: str):
		if payment_method not in VALID_PAYMENT_METHODS:
			frappe.throw("付款方式必須是：現金、匯款、信用卡、其他。")

	def _resolve_or_create_customer(self, customer_name: str, customer_phone: str):
		customer_meta = frappe.get_meta("Customer")
		for phone_field in ("mobile_no", "phone"):
			if customer_meta.has_field(phone_field):
				customer = frappe.db.get_value("Customer", {phone_field: customer_phone}, "name")
				if customer:
					return customer

		customer = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
		if customer:
			return customer

		customer_doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_type": "Individual",
				"customer_group": self._resolve_customer_group(),
				"territory": self._resolve_territory(),
			}
		)
		if customer_meta.has_field("mobile_no"):
			customer_doc.mobile_no = customer_phone
		elif customer_meta.has_field("phone"):
			customer_doc.phone = customer_phone

		# 只建立 Customer 主檔，不建立 Address / Contact / Payment，避免訂金紀錄誤變正式收款流程。
		customer_doc.insert()
		return customer_doc.name

	def _resolve_customer_group(self):
		for group_name in ("Individual", "個人"):
			if frappe.db.exists("Customer Group", {"name": group_name, "is_group": 0}):
				return group_name

		customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name", order_by="name asc")
		if not customer_group:
			frappe.throw("找不到可用的非群組 Customer Group，無法建立 ERPNext Customer。")
		return customer_group

	def _resolve_territory(self):
		for territory_name in ("Taiwan", "台灣"):
			if frappe.db.exists("Territory", {"name": territory_name, "is_group": 0}):
				return territory_name

		territory = frappe.db.get_value("Territory", {"is_group": 0}, "name", order_by="name asc")
		if not territory:
			frappe.throw("找不到可用的非群組 Territory，無法建立 ERPNext Customer。")
		return territory

	def _vehicle_title(self, vehicle):
		return " ".join(str(part) for part in (vehicle.year, vehicle.brand, vehicle.model) if part)


@frappe.whitelist()
def create_reservation(
	vehicle_name: str,
	customer_name: str,
	customer_phone: str,
	deposit_amount,
	payment_method: str,
	deposit_date=None,
	payment_reference: str | None = None,
	notes: str | None = None,
	customer: str | None = None,
):
	service = VehicleReservationService()
	return service.create_reservation(
		vehicle_name=vehicle_name,
		customer_name=customer_name,
		customer_phone=customer_phone,
		deposit_amount=deposit_amount,
		payment_method=payment_method,
		deposit_date=deposit_date,
		payment_reference=payment_reference,
		notes=notes,
		customer=customer,
	)


@frappe.whitelist()
def cancel_reservation(reservation_name: str, reason: str):
	service = VehicleReservationService()
	return service.cancel_reservation(reservation_name, reason)


@frappe.whitelist()
def cancel_active_reservation_for_vehicle(vehicle_name: str, reason: str):
	service = VehicleReservationService()
	return service.cancel_active_reservation_for_vehicle(vehicle_name, reason)


@frappe.whitelist()
def get_active_reservation_for_vehicle(vehicle_name: str):
	service = VehicleReservationService()
	return service.get_active_reservation_for_vehicle(vehicle_name)


def verify_vehicle_reservation_service():
	service = VehicleReservationService()
	vehicle = None
	item_name = None
	stock_entry_name = None
	serial_no = None
	reservation_name = None
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
				"license_plate": "VERIFY-RESERVE",
				"vin": f"VERIFY-RESERVE-{frappe.generate_hash(length=10)}",
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
		vehicle.reload()
		if vehicle.status != "上架中":
			frappe.throw("Vehicle Reservation Service verification requires status 上架中 before reservation.")

		before_counts = _reservation_verification_doc_counts()
		before_serial_no_modified = frappe.db.get_value("Serial No", serial_no, "modified") if serial_no else None

		reservation_result = service.create_reservation(
			vehicle_name=vehicle.name,
			customer_name="王小明",
			customer_phone="0912345678",
			deposit_amount=10000,
			payment_method="現金",
			deposit_date=nowdate(),
			payment_reference="VERIFY",
		)
		reservation_name = reservation_result.get("reservation")
		customer_name = reservation_result.get("customer")
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		vehicle.reload()

		if reservation.status != "有效":
			frappe.throw("Vehicle Reservation Service verification did not create active reservation.")
		if vehicle.status != "保留中":
			frappe.throw("Vehicle Reservation Service verification did not update vehicle status to 保留中.")
		if not reservation.customer:
			frappe.throw("Vehicle Reservation Service verification did not create/link Customer.")
		if flt(reservation.deposit_amount) != 10000:
			frappe.throw("Vehicle Reservation Service verification deposit amount mismatch.")

		duplicate_reservation_blocked = False
		try:
			service.create_reservation(
				vehicle_name=vehicle.name,
				customer_name="王小明",
				customer_phone="0912345678",
				deposit_amount=10000,
				payment_method="現金",
			)
		except frappe.ValidationError:
			duplicate_reservation_blocked = True
		if not duplicate_reservation_blocked:
			frappe.throw("Vehicle Reservation Service verification allowed duplicate active reservation.")

		after_reservation_counts = _reservation_verification_doc_counts()
		if after_reservation_counts != before_counts:
			frappe.throw("Vehicle Reservation Service must not create stock, invoice, payment, delivery, or journal documents.")

		cancel_result = service.cancel_active_reservation_for_vehicle(vehicle.name, reason="VERIFY CANCEL")
		reservation.reload()
		vehicle.reload()
		if reservation.status != "已取消":
			frappe.throw("Vehicle Reservation Service verification did not cancel reservation.")
		if not reservation.cancellation_reason:
			frappe.throw("Vehicle Reservation Service verification did not record cancellation reason.")
		if vehicle.status != "上架中":
			frappe.throw("Vehicle Reservation Service verification did not return vehicle status to 上架中.")

		after_cancel_counts = _reservation_verification_doc_counts()
		if after_cancel_counts != before_counts:
			frappe.throw("Vehicle Reservation Service cancel must not create stock, invoice, payment, delivery, or journal documents.")
		if serial_no and frappe.db.get_value("Serial No", serial_no, "modified") != before_serial_no_modified:
			frappe.throw("Vehicle Reservation Service must not modify Serial No.")

		verification = {
			"vehicle_name": vehicle.name,
			"stock_no": stock_no,
			"reservation": reservation_name,
			"customer": customer_name,
			"status_after_reservation": reservation_result.get("status"),
			"status_after_cancel": cancel_result.get("status"),
			"duplicate_reservation_blocked": duplicate_reservation_blocked,
			"stock_entry_count_unchanged": after_cancel_counts["Stock Entry"] == before_counts["Stock Entry"],
			"purchase_invoice_count_unchanged": after_cancel_counts["Purchase Invoice"] == before_counts["Purchase Invoice"],
			"sales_invoice_count_unchanged": after_cancel_counts["Sales Invoice"] == before_counts["Sales Invoice"],
			"payment_entry_count_unchanged": after_cancel_counts["Payment Entry"] == before_counts["Payment Entry"],
			"delivery_note_count_unchanged": after_cancel_counts["Delivery Note"] == before_counts["Delivery Note"],
			"journal_entry_count_unchanged": after_cancel_counts["Journal Entry"] == before_counts["Journal Entry"],
			"cleaned_up": False,
		}
	finally:
		try:
			stock_entry_cancelled = False
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
				frappe.db.set_value(
					"Used Car Vehicle",
					vehicle.name,
					{"serial_no": None, "stock_entry": None, "item": None},
				)
				frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
			if stock_entry_cancelled and not serial_existed_before and serial_no and frappe.db.exists("Serial No", serial_no):
				try:
					frappe.delete_doc("Serial No", serial_no, force=True)
				except Exception:
					# 庫存歷史可能限制序號刪除，清理不得繞過 ERPNext 標準保護。
					verification["serial_no_cleanup_skipped"] = True
			if stock_entry_cancelled and not item_existed_before and item_name and frappe.db.exists("Item", item_name):
				try:
					frappe.delete_doc("Item", item_name, force=True)
				except Exception:
					# Item 若已被庫存歷史引用，保留標準完整性限制並回報。
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
			frappe.throw(f"Vehicle Reservation Service verification cleanup failed: {exc}")

	return verification


def _reservation_verification_doc_counts():
	return {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
