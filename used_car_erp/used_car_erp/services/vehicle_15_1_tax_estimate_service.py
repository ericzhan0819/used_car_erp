import frappe
from frappe.utils import flt


ROUNDING_TOLERANCE = 0.01

EXCLUDED_COST_CATEGORIES = [
	"整備費",
	"維修費",
	"美容費",
	"拍場費",
	"代辦費",
	"其他後續支出",
]

FORMULA = {
	"output_tax": "sale_price / 1.05 * 0.05",
	"input_tax_estimate": "purchase_price / 1.05 * 0.05",
	"allowed_deduction": "min(input_tax_estimate, output_tax)",
	"estimated_business_tax": "output_tax - allowed_deduction",
}

REPORT_KEYS = (
	"status",
	"estimate_reliable",
	"ready_for_vehicle_page",
	"vehicle",
	"vehicle_status",
	"sales_invoice",
	"sales_invoice_docstatus",
	"purchase_price",
	"purchase_price_source",
	"sale_price",
	"sale_price_source",
	"vehicle_tax_mode",
	"purchase_source_type",
	"purchase_document_type",
	"tax_review_status",
	"tax_review_note",
	"tax_mode_applicability",
	"output_tax_raw",
	"input_tax_estimate_raw",
	"allowed_deduction_raw",
	"estimated_business_tax_raw",
	"output_tax_display",
	"input_tax_estimate_display",
	"allowed_deduction_display",
	"estimated_business_tax_display",
	"excluded_cost_categories",
	"formula",
	"summary_cards",
	"validations",
	"warnings",
	"blocking_errors",
)

OPTIONAL_VEHICLE_FIELDS = (
	"vehicle_tax_mode",
	"purchase_source_type",
	"purchase_document_type",
	"tax_review_status",
	"tax_review_note",
)


class Vehicle151TaxEstimateService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, vehicle_name=None, sales_invoice=None):
		vehicle = self._resolve_target_vehicle(vehicle_name=vehicle_name, sales_invoice=sales_invoice)
		if not vehicle:
			self._block("找不到符合條件的 15-1 稅務估算 target。")
			self._set_status()
			return self.report

		invoice = self._resolve_invoice(vehicle, sales_invoice=sales_invoice)
		self._read_vehicle(vehicle)
		self._read_invoice(invoice)
		self._resolve_purchase_price(vehicle)
		self._resolve_sale_price(vehicle, invoice)
		self._apply_tax_mode_rules()
		self._calculate_estimate()
		self._build_summary_cards()
		self._set_status()
		return self.report

	def find_candidates(self, limit=10):
		return _get_vehicle_15_1_tax_estimate_candidates(limit=limit)

	def _new_report(self):
		list_keys = {"summary_cards", "validations", "warnings", "blocking_errors"}
		return {key: [] if key in list_keys else None for key in REPORT_KEYS} | {
			"status": "fail",
			"estimate_reliable": False,
			"ready_for_vehicle_page": False,
			"excluded_cost_categories": list(EXCLUDED_COST_CATEGORIES),
			"formula": dict(FORMULA),
		}

	def _resolve_target_vehicle(self, vehicle_name=None, sales_invoice=None):
		if vehicle_name:
			self.report["vehicle"] = vehicle_name
			return frappe.get_doc("Used Car Vehicle", vehicle_name) if frappe.db.exists("Used Car Vehicle", vehicle_name) else None
		if sales_invoice:
			self.report["sales_invoice"] = sales_invoice
			vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": sales_invoice}, "name")
			return frappe.get_doc("Used Car Vehicle", vehicle_name) if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name) else None
		candidates = self.find_candidates(limit=1)
		vehicle_name = candidates[0].get("vehicle") if candidates else None
		return frappe.get_doc("Used Car Vehicle", vehicle_name) if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name) else None

	def _resolve_invoice(self, vehicle, sales_invoice=None):
		invoice_name = sales_invoice or vehicle.get("sales_invoice")
		self.report["sales_invoice"] = invoice_name
		if not invoice_name:
			return None
		if not frappe.db.exists("Sales Invoice", invoice_name):
			self._block(f"Vehicle linked Sales Invoice 不存在：{invoice_name}")
			return None
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		if int(getattr(invoice, "docstatus", 0) or 0) not in (0, 1):
			self._block("Sales Invoice docstatus 必須是 0 或 1。")
		return invoice

	def _read_vehicle(self, vehicle):
		self.report.update({"vehicle": vehicle.get("name"), "vehicle_status": vehicle.get("status")})
		for fieldname in OPTIONAL_VEHICLE_FIELDS:
			if self._vehicle_has_field(fieldname):
				self.report[fieldname] = vehicle.get(fieldname)
			else:
				self._warn(f"Used Car Vehicle 缺少 {fieldname} 欄位，僅提供 basic preview。")

	def _read_invoice(self, invoice):
		if invoice:
			self.report["sales_invoice_docstatus"] = int(getattr(invoice, "docstatus", 0) or 0)

	def _resolve_purchase_price(self, vehicle):
		if not self._vehicle_has_field("purchase_price"):
			self._block("Used Car Vehicle 缺少 purchase_price 欄位，無法估算 15-1 購入可扣抵稅額。")
			return
		purchase_price = flt(vehicle.get("purchase_price"))
		self.report["purchase_price"] = purchase_price
		self.report["purchase_price_source"] = "used_car_vehicle_purchase_price"
		if purchase_price <= 0:
			self._block("purchase_price 必須大於 0；purchase_price = 購車價，不包含整備、維修、美容、拍場、代辦或其他後續費用。")
		else:
			self._validate("purchase_price 來自 Used Car Vehicle.purchase_price。")

	def _resolve_sale_price(self, vehicle, invoice):
		vehicle_sold_price = flt(vehicle.get("sold_price")) if self._vehicle_has_field("sold_price") else 0
		invoice_grand_total = flt(getattr(invoice, "grand_total", 0)) if invoice and int(getattr(invoice, "docstatus", 0) or 0) in (0, 1) else 0

		if vehicle_sold_price > 0 and invoice_grand_total > 0 and abs(vehicle_sold_price - invoice_grand_total) > ROUNDING_TOLERANCE:
			self._warn("Vehicle.sold_price 與 Sales Invoice grand_total 不一致，預設以 Sales Invoice grand_total 作為正式文件金額。")
			self.report["sale_price"] = invoice_grand_total
			self.report["sale_price_source"] = "sales_invoice_grand_total"
		elif vehicle_sold_price > 0:
			self.report["sale_price"] = vehicle_sold_price
			self.report["sale_price_source"] = "used_car_vehicle_sold_price"
		elif invoice_grand_total > 0:
			self.report["sale_price"] = invoice_grand_total
			self.report["sale_price_source"] = "sales_invoice_grand_total"
		else:
			self._block("缺少售車價；需 Used Car Vehicle.sold_price 或 docstatus 0/1 Sales Invoice grand_total。")

		if self.report.get("sale_price") is not None and flt(self.report.get("sale_price")) <= 0:
			self._block("sale_price 必須大於 0。")

	def _apply_tax_mode_rules(self):
		mode = self.report.get("vehicle_tax_mode")
		if mode == "15-1 特殊扣抵" or (mode and "15-1" in mode):
			self.report["tax_mode_applicability"] = "15-1 特殊扣抵，適用 15-1 公式估算售車營業稅。"
		elif mode in ("待確認", "拍場需確認", None, ""):
			self.report["tax_mode_applicability"] = "稅務模式待確認，僅提供 15-1 preview，不代表正式適用結果。"
			self._warn("vehicle_tax_mode 未確認，estimate_reliable = False。")
		elif mode == "一般發票扣抵":
			self.report["tax_mode_applicability"] = "一般發票扣抵，不使用 15-1 公式"
			self._warn("vehicle_tax_mode 為一般發票扣抵，15-1 不作為正式估算結果。")
		elif mode == "不可扣抵":
			self.report["tax_mode_applicability"] = "不可扣抵，購入可扣抵稅額以 0 計算。"
		else:
			self.report["tax_mode_applicability"] = f"未識別稅務模式：{mode}，僅提供 preview。"
			self._warn("vehicle_tax_mode 不是已知值，estimate_reliable = False。")

	def _calculate_estimate(self):
		if self.report["blocking_errors"]:
			return
		purchase_price = flt(self.report.get("purchase_price"))
		sale_price = flt(self.report.get("sale_price"))
		output_tax = sale_price / 1.05 * 0.05
		input_tax_estimate = purchase_price / 1.05 * 0.05
		if self.report.get("vehicle_tax_mode") == "不可扣抵":
			allowed_deduction = 0
		else:
			allowed_deduction = min(input_tax_estimate, output_tax)
		estimated_business_tax = output_tax - allowed_deduction
		self.report.update(
			{
				"output_tax_raw": round(output_tax, 2),
				"input_tax_estimate_raw": round(input_tax_estimate, 2),
				"allowed_deduction_raw": round(allowed_deduction, 2),
				"estimated_business_tax_raw": round(estimated_business_tax, 2),
				"output_tax_display": round(output_tax),
				"input_tax_estimate_display": round(input_tax_estimate),
				"allowed_deduction_display": round(allowed_deduction),
				"estimated_business_tax_display": round(estimated_business_tax),
			}
		)

	def _build_summary_cards(self):
		if self.report["blocking_errors"]:
			return
		self.report["summary_cards"] = [
			{"label": "售車銷項稅額", "amount": self.report.get("output_tax_display")},
			{"label": "15-1 可扣抵估算", "amount": self.report.get("allowed_deduction_display")},
			{"label": "預估本車營業稅", "amount": self.report.get("estimated_business_tax_display")},
		]

	def _vehicle_has_field(self, fieldname):
		try:
			return frappe.get_meta("Used Car Vehicle").has_field(fieldname)
		except Exception:
			return True

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _warn(self, message):
		self.report["warnings"].append(message)

	def _validate(self, message):
		self.report["validations"].append(message)

	def _set_status(self):
		self.report["ready_for_vehicle_page"] = bool(self.report.get("vehicle") and not self.report["blocking_errors"])
		if self.report["blocking_errors"]:
			self.report["status"] = "fail"
		elif self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"
		self.report["estimate_reliable"] = self.report["status"] == "pass"


def _get_vehicle_15_1_tax_estimate_candidates(limit=10):
	vehicles = frappe.db.get_all(
		"Used Car Vehicle",
		filters={"status": ["in", ["已售出", "保留中", "庫存中"]], "purchase_price": [">", 0]},
		fields=("name", "status", "purchase_price", "sold_price", "sales_invoice", "vehicle_tax_mode", "modified"),
		order_by="modified desc",
		limit=limit,
	)
	results = []
	for vehicle in vehicles:
		if not vehicle.get("sold_price") and not vehicle.get("sales_invoice"):
			continue
		invoice_name = vehicle.get("sales_invoice")
		if invoice_name and not frappe.db.exists("Sales Invoice", invoice_name):
			continue
		if invoice_name and _is_qa_sales_invoice(invoice_name):
			continue
		results.append(
			{
				"vehicle": vehicle.get("name"),
				"vehicle_status": vehicle.get("status"),
				"purchase_price": flt(vehicle.get("purchase_price")),
				"sold_price": flt(vehicle.get("sold_price")),
				"sales_invoice": invoice_name,
				"vehicle_tax_mode": vehicle.get("vehicle_tax_mode"),
				"modified": vehicle.get("modified"),
			}
		)
	return results


def _is_qa_sales_invoice(invoice_name):
	if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
		return False
	invoice = frappe.get_doc("Sales Invoice", invoice_name)
	text = "\n".join(str(getattr(invoice, fieldname, "") or "") for fieldname in ("remarks", "user_remark", "title"))
	return "P1-ACC-6E" in text or "QA" in text


@frappe.whitelist()
def run_vehicle_15_1_tax_estimate(vehicle_name=None, sales_invoice=None):
	return Vehicle151TaxEstimateService().run(vehicle_name=vehicle_name, sales_invoice=sales_invoice)


@frappe.whitelist()
def find_vehicle_15_1_tax_estimate_candidates(limit=10):
	return Vehicle151TaxEstimateService().find_candidates(limit=limit)
