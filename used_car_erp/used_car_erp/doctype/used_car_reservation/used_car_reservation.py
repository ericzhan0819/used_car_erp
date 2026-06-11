import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate


VALID_RESERVATION_STATUSES = ("有效", "已取消", "已完成")


class UsedCarReservation(Document):
	def before_insert(self):
		if not self.reservation_no:
			self.reservation_no = _get_next_reservation_no()
		if not self.status:
			self.status = "有效"
		if not self.deposit_date:
			self.deposit_date = nowdate()

	def validate(self):
		self._prevent_reservation_no_change()
		self._validate_required_fields()
		self._validate_status()
		self._validate_deposit_amount()

	def _prevent_reservation_no_change(self):
		if self.is_new():
			return

		old_reservation_no = frappe.db.get_value("Used Car Reservation", self.name, "reservation_no")
		if old_reservation_no and self.reservation_no != old_reservation_no:
			frappe.throw("保留單號由系統自動產生，不可手動修改。")

	def _validate_required_fields(self):
		if not self.vehicle:
			frappe.throw("車輛為必填。")
		if not self.customer_name:
			frappe.throw("客戶姓名為必填。")
		if not self.customer_phone:
			frappe.throw("客戶電話為必填。")

	def _validate_status(self):
		if self.status not in VALID_RESERVATION_STATUSES:
			frappe.throw("保留狀態必須是：有效、已取消、已完成。")

	def _validate_deposit_amount(self):
		if flt(self.deposit_amount) <= 0:
			frappe.throw("訂金金額必須大於 0。")


def _get_next_reservation_no():
	period = nowdate().replace("-", "")[:6]
	prefix = f"RSV-{period}-"
	rows = frappe.db.sql(
		"""
		select reservation_no
		from `tabUsed Car Reservation`
		where reservation_no like %s
		""",
		(f"{prefix}%",),
		as_dict=True,
	)

	max_number = 0
	for row in rows:
		try:
			max_number = max(max_number, int(row.reservation_no.replace(prefix, "", 1)))
		except (TypeError, ValueError):
			# 避免歷史資料或人工匯入編號格式異常時，中斷新增保留流程。
			continue

	return f"{prefix}{max_number + 1:04d}"
