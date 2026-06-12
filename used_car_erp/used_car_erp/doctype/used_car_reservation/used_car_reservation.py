import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate


VALID_RESERVATION_STATUSES = ("有效", "已取消", "已完成")
VALID_PAYMENT_METHODS = ("現金", "匯款", "信用卡", "其他")
ACCOUNTING_SERVICE_FIELDS = (
	"status",
	"money_flow",
	"voucher_draft",
	"journal_entry",
	"final_money_flow",
	"final_voucher_draft",
	"final_journal_entry",
	"final_payment_amount",
	"final_payment_date",
	"final_payment_method",
	"final_payment_reference",
	"final_payment_notes",
	"completed_at",
	"completed_by",
	"completion_note",
)


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
		self._prevent_accounting_link_change()
		self._validate_required_fields()
		self._validate_status()
		self._validate_deposit_amount()
		self._validate_final_payment_fields()

	def _prevent_reservation_no_change(self):
		if self.is_new():
			return

		old_reservation_no = frappe.db.get_value("Used Car Reservation", self.name, "reservation_no")
		if old_reservation_no and self.reservation_no != old_reservation_no:
			frappe.throw("保留單號由系統自動產生，不可手動修改。")

	def _prevent_accounting_link_change(self):
		if self.is_new():
			return

		old_values = frappe.db.get_value(
			"Used Car Reservation",
			self.name,
			ACCOUNTING_SERVICE_FIELDS,
			as_dict=True,
		)
		for fieldname in ACCOUNTING_SERVICE_FIELDS:
			if old_values and (self.get(fieldname) or "") != (old_values.get(fieldname) or "") and not getattr(self.flags, "ignore_accounting_link_validation", False):
				frappe.throw("保留狀態、金流紀錄、傳票草稿、正式會計傳票、尾款與成交確認欄位只能由系統服務回寫。")

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

	def _validate_final_payment_fields(self):
		if not self.final_payment_amount:
			return
		if flt(self.final_payment_amount) <= 0:
			frappe.throw("尾款金額必須大於 0。")
		if not self.final_payment_date:
			frappe.throw("尾款日期為必填。")
		if self.final_payment_method not in VALID_PAYMENT_METHODS:
			frappe.throw("尾款付款方式必須是：現金、匯款、信用卡、其他。")


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
