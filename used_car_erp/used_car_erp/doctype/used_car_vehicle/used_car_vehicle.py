import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


SALE_COMPLETION_FIELDS = (
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
)

FORMAL_DELIVERY_FIELDS = (
	"formal_delivery_status",
	"formal_delivery_posting_date",
	"sales_invoice",
	"advance_settlement_journal_entry",
	"formal_delivery_completed_at",
	"formal_delivery_completed_by",
	"formal_delivery_note",
)


class UsedCarVehicle(Document):
	def before_insert(self):
		self.stock_no = _get_next_stock_no()

	def validate(self):
		self._prevent_stock_no_change()
		self._prevent_manual_sale_completion_change()
		self._prevent_manual_formal_delivery_change()

	def _prevent_stock_no_change(self):
		if self.is_new():
			return

		old_stock_no = frappe.db.get_value("Used Car Vehicle", self.name, "stock_no")
		if old_stock_no and self.stock_no != old_stock_no:
			frappe.throw("車輛編號由系統自動產生，不可手動修改。")

	def _prevent_manual_sale_completion_change(self):
		if self.is_new() or self.flags.ignore_sale_completion_validation:
			return

		meta = frappe.get_meta("Used Car Vehicle")
		for fieldname in SALE_COMPLETION_FIELDS:
			if not meta.has_field(fieldname) or not self.has_value_changed(fieldname):
				continue
			# 成交摘要必須由確認成交 service 回寫，避免人工竄改造成訂金、尾款與正式傳票連結失真。
			frappe.throw("成交摘要欄位由確認成交流程維護，不可手動修改。")

	def _prevent_manual_formal_delivery_change(self):
		if self.is_new() or self.flags.ignore_formal_delivery_validation:
			return

		meta = frappe.get_meta("Used Car Vehicle")
		for fieldname in FORMAL_DELIVERY_FIELDS:
			if not meta.has_field(fieldname) or not self.has_value_changed(fieldname):
				continue
			# 正式交車入帳欄位只能由 service 寫入，避免人工建立銷售文件連結造成出庫與會計階段不一致。
			frappe.throw("正式交車入帳欄位由正式交車流程維護，不可手動修改。")


def _get_next_stock_no():
	period = nowdate().replace("-", "")[:6]
	prefix = f"VH-{period}-"
	rows = frappe.db.sql(
		"""
		select stock_no
		from `tabUsed Car Vehicle`
		where stock_no like %s
		""",
		(f"{prefix}%",),
		as_dict=True,
	)

	max_number = 0
	for row in rows:
		try:
			max_number = max(max_number, int(row.stock_no.replace(prefix, "", 1)))
		except (TypeError, ValueError):
			# 避免歷史資料或手動編號格式不正確時，中斷新增車輛流程。
			continue

	return f"{prefix}{max_number + 1:04d}"


def verify_test_vehicle_insert():
	# 這個函式只供 bench execute 做部署後驗證，避免在正式資料中留下測試車輛。
	period = nowdate().replace("-", "")[:6]
	auto_number_prefix = f"VH-{period}-"
	manual_stock_no = "MANUAL-SHOULD-NOT-BE-USED"
	vehicle = frappe.get_doc(
		{
			"doctype": "Used Car Vehicle",
			"stock_no": manual_stock_no,
			"vin": f"VERIFY-{frappe.generate_hash(length=10)}",
		}
	).insert()

	result = {
		"name": vehicle.name,
		"stock_no": vehicle.stock_no,
		"status": vehicle.status,
		"auto_number_prefix": auto_number_prefix,
		"manual_value_ignored": vehicle.stock_no != manual_stock_no,
		"doctype_exists": frappe.db.exists("DocType", "Used Car Vehicle"),
	}
	if not vehicle.stock_no.startswith(auto_number_prefix):
		frappe.throw("Used Car Vehicle stock_no was not auto-generated with the expected prefix.")
	if vehicle.name != vehicle.stock_no:
		frappe.throw("Used Car Vehicle name does not match stock_no.")
	if vehicle.status != "草稿":
		frappe.throw("Used Car Vehicle status default is not 草稿.")
	if vehicle.stock_no == manual_stock_no:
		frappe.throw("Used Car Vehicle accepted a manually supplied stock_no.")

	frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
	frappe.db.commit()
	return result
