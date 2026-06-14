import frappe
from frappe.model.document import Document


class TaiwanAccountingItemAccountMapping(Document):
	def validate(self):
		self._validate_required_links()
		self._validate_account()
		self._validate_taiwan_accounting_item_code()
		self._validate_duplicate_active_mapping()
		self._validate_single_default_for_purpose()

	def _validate_required_links(self):
		if not self.company:
			frappe.throw("公司為必填。")
		if not self.account:
			frappe.throw("ERPNext 科目為必填。")
		if not self.taiwan_accounting_item_code:
			frappe.throw("台灣會計項目代號為必填。")
		if not self.mapping_purpose:
			frappe.throw("對應用途為必填。")

	def _validate_account(self):
		if not frappe.db.exists("Account", self.account):
			frappe.throw(f"ERPNext 科目不存在：{self.account}")

		account = frappe.get_doc("Account", self.account)

		if account.company != self.company:
			frappe.throw("ERPNext 科目所屬公司與 mapping 公司不一致。")

		if account.is_group:
			frappe.throw("ERPNext 科目為群組科目，不能用於官方會計項目 mapping。")

		if account.disabled:
			frappe.throw("ERPNext 科目已停用，不能用於官方會計項目 mapping。")

	def _validate_taiwan_accounting_item_code(self):
		if not frappe.db.exists("Taiwan Accounting Item Code", self.taiwan_accounting_item_code):
			frappe.throw(f"台灣會計項目代號不存在：{self.taiwan_accounting_item_code}")

		item_code = frappe.get_doc("Taiwan Accounting Item Code", self.taiwan_accounting_item_code)

		if not item_code.is_active:
			frappe.throw("停用中的台灣會計項目代號不能用於 active mapping。")

		# 注意：is_group_like 不阻擋 mapping，避免短期報表分類需要人工對應官方彙總項目時被系統誤擋。
		# 有些官方彙總項目，例如 0100001 營業收入總額，短期仍可能作為報表分類 mapping 使用。
		# 這裡不做 runtime 判斷，只保留會計人工決策空間。

	def _validate_duplicate_active_mapping(self):
		if not self.is_active:
			return

		duplicate = frappe.db.exists(
			"Taiwan Accounting Item Account Mapping",
			{
				"company": self.company,
				"account": self.account,
				"mapping_purpose": self.mapping_purpose,
				"is_active": 1,
				"name": ["!=", self.name],
			},
		)

		if duplicate:
			frappe.throw("同一公司、同一 ERPNext 科目、同一對應用途只能有一筆 active mapping。")

	def _validate_single_default_for_purpose(self):
		if not self.is_active or not self.is_default:
			return

		duplicate_default = frappe.db.exists(
			"Taiwan Accounting Item Account Mapping",
			{
				"company": self.company,
				"mapping_purpose": self.mapping_purpose,
				"is_default": 1,
				"is_active": 1,
				"name": ["!=", self.name],
			},
		)

		if duplicate_default:
			frappe.throw("同一公司、同一對應用途只能有一筆 active default mapping。")


def verify_taiwan_accounting_item_account_mapping_doctype():
	meta = frappe.get_meta("Taiwan Accounting Item Account Mapping")
	required_fields = {
		"company",
		"account",
		"taiwan_accounting_item_code",
		"mapping_purpose",
		"is_default",
		"is_active",
		"note",
	}

	missing_fields = sorted(fieldname for fieldname in required_fields if not meta.has_field(fieldname))

	code_meta = frappe.get_meta("Taiwan Accounting Item Code")
	item_code_exists = frappe.db.exists("Taiwan Accounting Item Code", "0202134")

	return {
		"doctype_exists": frappe.db.exists("DocType", "Taiwan Accounting Item Account Mapping"),
		"missing_fields": missing_fields,
		"taiwan_accounting_item_code_doctype_exists": frappe.db.exists("DocType", "Taiwan Accounting Item Code"),
		"taiwan_accounting_item_code_has_code_field": code_meta.has_field("code"),
		"sample_output_vat_code_exists": bool(item_code_exists),
		"uses_link_to_taiwan_accounting_item_code": meta.get_field("taiwan_accounting_item_code").options
		== "Taiwan Accounting Item Code",
	}
