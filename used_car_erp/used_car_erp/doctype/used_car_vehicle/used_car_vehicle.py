import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

from used_car_erp.used_car_erp.services.vehicle_formal_delivery_service import (
	CANCELLED_SALES_INVOICE_RELINK_MESSAGE,
	MISSING_SALES_INVOICE_LINK_MESSAGE,
	SUBMITTED_SALES_INVOICE_LOCKED_MESSAGE,
	is_vehicle_formally_accounting_locked,
	sync_sales_invoice_draft_from_vehicle,
)


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

SALE_WORKFLOW_FIELDS = (
	"customer",
	"sold_price",
	"sold_date",
	"delivery_date",
	"expected_delivery_date",
	"sales_staff",
	"sales_note",
	"vehicle_tax_mode",
	"tax_review_status",
	"tax_review_note",
)

VAT_DEDUCTIBLE_PURCHASE_DOCUMENT_TYPES = {"統一發票"}

ARTICLE_15_1_PURCHASE_DOCUMENT_TYPES = {
	"買賣合約",
	"讓渡書",
	"匯款紀錄",
	"收據",
	"未取得",
}

TAX_REVIEW_REQUIRED_PURCHASE_DOCUMENT_TYPES = {
	"拍場單據",
	"其他",
	None,
	"",
}


class UsedCarVehicle(Document):
	def before_insert(self):
		self.stock_no = _get_next_stock_no()

	def validate(self):
		self._prevent_stock_no_change()
		self._validate_tax_metadata()
		self._derive_tax_mode_from_purchase_evidence()
		self._protect_locked_sale_workflow_fields()
		self._prevent_manual_sale_completion_change()
		self._prevent_manual_formal_delivery_change()
		self._sync_sales_invoice_draft_when_sale_workflow_changes()

	def _prevent_stock_no_change(self):
		if self.is_new():
			return

		old_stock_no = frappe.db.get_value("Used Car Vehicle", self.name, "stock_no")
		if old_stock_no and self.stock_no != old_stock_no:
			frappe.throw("車輛編號由系統自動產生，不可手動修改。")

	def _validate_tax_metadata(self):
		meta = frappe.get_meta("Used Car Vehicle")
		if not meta.has_field("purchase_price"):
			return
		if self.purchase_price is not None and self.purchase_price < 0:
			# 買入金額是後續稅務估算基礎，先阻擋負數以避免產生錯誤的營業稅與毛利資料。
			frappe.throw("買入金額不可為負數。")

	def _derive_tax_mode_from_purchase_evidence(self):
		meta = frappe.get_meta("Used Car Vehicle")
		if not meta.has_field("vehicle_tax_mode") or not meta.has_field("purchase_document_type"):
			return

		tax_mode, review_status = derive_vehicle_tax_mode_from_purchase_document_type(
			self.get("purchase_document_type")
		)

		# 車輛頁只記錄買入憑證，稅務模式由後端推導，避免使用者在車輛頁手動處理正式稅務。
		self.vehicle_tax_mode = tax_mode

		if meta.has_field("tax_review_status"):
			self.tax_review_status = review_status

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

	def _protect_locked_sale_workflow_fields(self):
		if self.is_new() or self.flags.ignore_sale_workflow_lock_validation:
			return
		if not is_vehicle_formally_accounting_locked(self):
			return

		meta = frappe.get_meta("Used Car Vehicle")
		for fieldname in SALE_WORKFLOW_FIELDS:
			if not meta.has_field(fieldname) or not self.has_value_changed(fieldname):
				continue
			# 已提交的正式銷售文件代表會計與庫存已鎖定，直接改售車事實會造成 IDOR 式資料不一致與會計錯帳風險。
			frappe.throw(_get_locked_sale_workflow_message(self))

	def _sync_sales_invoice_draft_when_sale_workflow_changes(self):
		if self.is_new() or self.flags.ignore_sale_invoice_draft_sync:
			return
		if not self.sales_invoice:
			return

		meta = frappe.get_meta("Used Car Vehicle")
		changed = any(meta.has_field(fieldname) and self.has_value_changed(fieldname) for fieldname in SALE_WORKFLOW_FIELDS)
		if not changed:
			return

		# 只同步既有 Sales Invoice 草稿；submitted 發票會由鎖定檢查阻擋，避免繞過正式修正流程。
		sync_sales_invoice_draft_from_vehicle(self)


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


def derive_vehicle_tax_mode_from_purchase_document_type(purchase_document_type: str | None) -> tuple[str, str]:
	if purchase_document_type in VAT_DEDUCTIBLE_PURCHASE_DOCUMENT_TYPES:
		return "一般發票扣抵", "已初步判斷"

	if purchase_document_type in ARTICLE_15_1_PURCHASE_DOCUMENT_TYPES:
		return "15-1 特殊扣抵", "已初步判斷"

	return "待確認", "待確認"


def _get_locked_sale_workflow_message(vehicle):
	if not vehicle.get("sales_invoice") or not frappe.db.exists("Sales Invoice", vehicle.sales_invoice):
		return MISSING_SALES_INVOICE_LINK_MESSAGE
	docstatus = frappe.db.get_value("Sales Invoice", vehicle.sales_invoice, "docstatus")
	if docstatus == 2:
		return CANCELLED_SALES_INVOICE_RELINK_MESSAGE
	return SUBMITTED_SALES_INVOICE_LOCKED_MESSAGE


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
