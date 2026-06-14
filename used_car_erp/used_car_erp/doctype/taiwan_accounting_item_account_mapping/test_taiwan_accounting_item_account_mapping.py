import frappe
from frappe.tests.utils import FrappeTestCase


class TestTaiwanAccountingItemAccountMapping(FrappeTestCase):
	def setUp(self):
		self.company = self._make_company("_Test Taiwan Mapping Company")
		self.other_company = self._make_company("_Test Taiwan Mapping Other Company")
		self.account = self._make_account("_Test Taiwan Mapping Sales", self.company)
		self.other_account = self._make_account("_Test Taiwan Mapping Other Sales", self.company)
		self.other_company_account = self._make_account("_Test Taiwan Mapping Foreign", self.other_company)
		self.group_account = self._make_account("_Test Taiwan Mapping Group", self.company, is_group=1)
		self.disabled_account = self._make_account("_Test Taiwan Mapping Disabled", self.company, disabled=1)
		self._make_item_code("0100005", "營業成本", "Cost", "Profit and Loss")
		self._make_item_code("0202134", "銷項稅額", "Liability", "Balance Sheet")
		self._make_item_code("0300090", "營業成本", "InventoryCost", "Cost Statement")

	def tearDown(self):
		frappe.db.delete("Taiwan Accounting Item Account Mapping", {"company": ("in", [self.company, self.other_company])})
		frappe.db.delete(
			"Account",
			{"company": ("in", [self.company, self.other_company]), "account_name": ("like", "_Test Taiwan Mapping%")},
		)
		frappe.db.delete("Company", {"name": ("in", [self.company, self.other_company])})
		frappe.db.delete("Taiwan Accounting Item Code", {"code": ("in", ["0100005", "0202134", "0300090", "0999999"])})

	def test_valid_mapping_can_be_created(self):
		doc = self._make_mapping(self.account, "0202134", "Output VAT")

		self.assertEqual(doc.company, self.company)
		self.assertEqual(doc.taiwan_accounting_item_code, "0202134")

	def test_account_company_mismatch_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_mapping(self.other_company_account, "0202134", "Output VAT")

	def test_group_account_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_mapping(self.group_account, "0202134", "Output VAT")

	def test_disabled_account_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_mapping(self.disabled_account, "0202134", "Output VAT")

	def test_missing_taiwan_accounting_item_code_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_mapping(self.account, "0999999", "Output VAT")

	def test_inactive_taiwan_accounting_item_code_is_blocked(self):
		self._make_item_code("0999999", "停用測試", "Other", "Other", is_active=0)

		with self.assertRaises(frappe.ValidationError):
			self._make_mapping(self.account, "0999999", "Other")

	def test_duplicate_active_mapping_for_same_company_account_and_purpose_is_blocked(self):
		self._make_mapping(self.account, "0202134", "Output VAT")

		with self.assertRaises(frappe.ValidationError):
			self._make_mapping(self.account, "0100005", "Output VAT")

	def test_single_active_default_mapping_per_company_and_purpose_is_blocked(self):
		self._make_mapping(self.account, "0202134", "Output VAT", is_default=1)

		with self.assertRaises(frappe.ValidationError):
			self._make_mapping(self.other_account, "0202134", "Output VAT", is_default=1)

	def test_multiple_accounts_can_map_to_same_taiwan_accounting_item_code(self):
		first = self._make_mapping(self.account, "0202134", "Output VAT")
		second = self._make_mapping(self.other_account, "0202134", "Other")

		self.assertEqual(first.taiwan_accounting_item_code, second.taiwan_accounting_item_code)

	def test_duplicate_item_name_codes_can_both_be_used_for_mapping(self):
		first = self._make_mapping(self.account, "0100005", "COGS")
		second = self._make_mapping(self.other_account, "0300090", "Inventory")

		self.assertEqual(first.taiwan_accounting_item_code, "0100005")
		self.assertEqual(second.taiwan_accounting_item_code, "0300090")

	def _make_company(self, company_name):
		if frappe.db.exists("Company", company_name):
			return company_name

		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": company_name.replace("_Test Taiwan Mapping ", "TM")[:5].upper(),
				"default_currency": "TWD",
				"country": "Taiwan",
			}
		).insert(ignore_permissions=True)
		return company_name

	def _make_account(self, account_name, company, is_group=0, disabled=0):
		account = frappe.db.get_value("Account", {"account_name": account_name, "company": company})
		if account:
			frappe.db.set_value("Account", account, {"is_group": is_group, "disabled": disabled})
			return account

		return frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"company": company,
				"root_type": "Income",
				"report_type": "Profit and Loss",
				"is_group": is_group,
				"disabled": disabled,
			}
		).insert(ignore_permissions=True).name

	def _make_item_code(self, code, item_name, category, statement_type, is_active=1):
		if frappe.db.exists("Taiwan Accounting Item Code", code):
			frappe.db.set_value("Taiwan Accounting Item Code", code, "is_active", is_active)
			return code

		return frappe.get_doc(
			{
				"doctype": "Taiwan Accounting Item Code",
				"code": code,
				"item_name": item_name,
				"category": category,
				"statement_type": statement_type,
				"normal_balance": "Debit",
				"is_active": is_active,
				"source_year": "113",
			}
		).insert(ignore_permissions=True).name

	def _make_mapping(self, account, item_code, mapping_purpose, is_default=0, is_active=1):
		return frappe.get_doc(
			{
				"doctype": "Taiwan Accounting Item Account Mapping",
				"company": self.company,
				"account": account,
				"taiwan_accounting_item_code": item_code,
				"mapping_purpose": mapping_purpose,
				"is_default": is_default,
				"is_active": is_active,
			}
		).insert(ignore_permissions=True)
