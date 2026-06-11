import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate


VALID_MONEY_FLOW_STATUSES = ("待審核", "已入帳", "已作廢")
VALID_FLOW_TYPES = ("訂金收款", "尾款收款", "貸款撥款", "退款", "其他")
VALID_PAYMENT_METHODS = ("現金", "匯款", "信用卡", "其他")


class UsedCarMoneyFlow(Document):
	def before_insert(self):
		if not self.money_flow_no:
			self.money_flow_no = _get_next_money_flow_no()
		if not self.status:
			self.status = "待審核"
		if not self.flow_type:
			self.flow_type = "訂金收款"
		if not self.direction:
			self.direction = "收入"

	def validate(self):
		self._prevent_money_flow_no_change()
		self._validate_status()
		self._validate_flow_type()
		self._validate_required_fields()
		self._validate_amount()
		self._validate_payment_method()

	def _prevent_money_flow_no_change(self):
		if self.is_new():
			return

		old_money_flow_no = frappe.db.get_value("Used Car Money Flow", self.name, "money_flow_no")
		if old_money_flow_no and self.money_flow_no != old_money_flow_no:
			frappe.throw("金流編號由系統自動產生，不可手動修改。")

	def _validate_status(self):
		if self.status not in VALID_MONEY_FLOW_STATUSES:
			frappe.throw("金流狀態必須是：待審核、已入帳、已作廢。")

	def _validate_flow_type(self):
		if self.flow_type not in VALID_FLOW_TYPES:
			frappe.throw("金流類型必須是：訂金收款、尾款收款、貸款撥款、退款、其他。")

	def _validate_required_fields(self):
		if not self.vehicle:
			frappe.throw("車輛為必填。")
		if not self.payment_date:
			frappe.throw("付款日期為必填。")
		if not self.payment_method:
			frappe.throw("付款方式為必填。")

	def _validate_amount(self):
		if flt(self.amount) <= 0:
			frappe.throw("金流金額必須大於 0。")

	def _validate_payment_method(self):
		if self.payment_method not in VALID_PAYMENT_METHODS:
			frappe.throw("付款方式必須是：現金、匯款、信用卡、其他。")


def _get_next_money_flow_no():
	period = nowdate().replace("-", "")[:6]
	prefix = f"MF-{period}-"
	rows = frappe.db.sql(
		"""
		select money_flow_no
		from `tabUsed Car Money Flow`
		where money_flow_no like %s
		""",
		(f"{prefix}%",),
		as_dict=True,
	)

	max_number = 0
	for row in rows:
		try:
			max_number = max(max_number, int(row.money_flow_no.replace(prefix, "", 1)))
		except (TypeError, ValueError):
			# 歷史匯入資料若編號格式異常，不應中斷後續金流紀錄建立。
			continue

	return f"{prefix}{max_number + 1:04d}"
