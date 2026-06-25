import frappe
from frappe.model.document import Document


VALID_ACCOUNT_TYPES = ("現金", "銀行", "其他")


class UsedCarCashAccount(Document):
	def validate(self):
		self._validate_account_type()

	def _validate_account_type(self):
		if self.account_type not in VALID_ACCOUNT_TYPES:
			frappe.throw("帳戶類型必須是：現金、銀行、其他。")
