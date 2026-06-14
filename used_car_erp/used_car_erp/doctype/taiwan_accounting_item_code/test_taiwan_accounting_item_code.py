import frappe
from frappe.tests.utils import FrappeTestCase


class TestTaiwanAccountingItemCode(FrappeTestCase):
	def tearDown(self):
		frappe.db.delete("Taiwan Accounting Item Code", {"code": ("in", ["0100005", "0300090", "04B0001"])})

	def test_duplicate_item_name_with_different_codes_can_coexist(self):
		self._make_item_code("0100005", "營業成本", "Cost", "Profit and Loss")
		self._make_item_code("0300090", "營業成本", "InventoryCost", "Cost Statement")

		codes = frappe.get_all(
			"Taiwan Accounting Item Code",
			filters={"item_name": "營業成本"},
			pluck="name",
		)

		self.assertEqual(sorted(codes), ["0100005", "0300090"])

	def test_code_is_stripped_and_uppercased(self):
		doc = self._make_item_code(" 04b0001 ", "測試項目", "Other", "Other")

		self.assertEqual(doc.name, "04B0001")
		self.assertEqual(doc.code, "04B0001")

	def test_invalid_code_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_item_code("020213", "銷項稅額", "Liability", "Balance Sheet")

	def test_empty_item_name_is_blocked(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_item_code("0202134", " ", "Liability", "Balance Sheet")

	def _make_item_code(self, code, item_name, category, statement_type):
		return frappe.get_doc(
			{
				"doctype": "Taiwan Accounting Item Code",
				"code": code,
				"item_name": item_name,
				"category": category,
				"statement_type": statement_type,
				"normal_balance": "Debit",
				"source_year": "113",
			}
		).insert(ignore_permissions=True)
