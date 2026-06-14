import re

import frappe
from frappe.model.document import Document


CODE_PATTERN = re.compile(r"^[0-9A-Z]{7}$")


class TaiwanAccountingItemCode(Document):
	def validate(self):
		self._normalize_code()
		self._validate_code()
		self._validate_item_name()

	def _normalize_code(self):
		if self.code:
			self.code = self.code.strip().upper()

	def _validate_code(self):
		if not self.code:
			frappe.throw("會計項目代號為必填。")
		if not CODE_PATTERN.match(self.code):
			frappe.throw("會計項目代號格式必須為 7 碼英數字，例如 0202134 或 04B0001。")

	def _validate_item_name(self):
		if not self.item_name or not self.item_name.strip():
			frappe.throw("項目中文名稱為必填。")
		self.item_name = self.item_name.strip()


def verify_taiwan_accounting_item_code_seed():
	expected_codes = {
		"0100001",
		"0100004",
		"0100005",
		"0201130",
		"0201131",
		"0300090",
		"0201111",
		"0201112",
		"0201123",
		"0201129",
		"0201144",
		"0201145",
		"0202132",
		"0202134",
		"0202121",
		"0202130",
		"0202136",
		"0202137",
		"0202138",
		"0100016",
		"0100017",
		"0100018",
		"0100019",
		"0100022",
		"0100030",
		"0100032",
	}

	missing = []
	for code in expected_codes:
		if not frappe.db.exists("Taiwan Accounting Item Code", code):
			missing.append(code)

	duplicate_name_codes = frappe.get_all(
		"Taiwan Accounting Item Code",
		filters={"item_name": "營業成本"},
		pluck="name",
	)

	return {
		"expected_count": len(expected_codes),
		"missing": sorted(missing),
		"business_cost_codes": sorted(duplicate_name_codes),
		"business_cost_duplicate_name_ok": sorted(duplicate_name_codes) == ["0100005", "0300090"],
	}
