import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.vehicle_15_1_tax_estimate_service import Vehicle151TaxEstimateService


ROUNDING_TOLERANCE = 0.01

EXCLUDED_FROM_15_1_TAX_BASE = ["整備費", "維修費", "美容費", "拍場費", "代辦費", "其他後續支出"]
EXCLUDED_FROM_MANAGEMENT_PROFIT = [
	"訂金收款",
	"尾款收款",
	"GL Entry 技術分錄",
	"Stock Ledger Entry 技術分錄",
	"15-1 可扣抵估算",
	"Sales Invoice outstanding_amount",
]
PURCHASE_COST_CATEGORIES = {"購車價", "買車價", "purchase_price", "purchase price"}
DIRECT_COST_CATEGORY_MAP = {
	"整備": "整備費",
	"整備費": "整備費",
	"維修": "維修費",
	"維修費": "維修費",
	"美容": "美容費",
	"美容費": "美容費",
	"拍場費": "拍場費",
	"代辦費": "代辦費",
	"過戶相關": "代辦費",
}
OTHER_INCOME_FLOW_TYPES = {"其他收入", "收入", "其他"}
SALE_COLLECTION_FLOW_TYPES = {"訂金收款", "尾款收款", "貸款撥款"}

REPORT_KEYS = (
	"status",
	"ready_for_vehicle_page",
	"vehicle",
	"vehicle_status",
	"sales_invoice",
	"sales_invoice_docstatus",
	"sale_price",
	"sale_price_source",
	"purchase_price",
	"purchase_price_source",
	"direct_cost_total",
	"direct_cost_rows",
	"cost_breakdown",
	"unmapped_cost_categories",
	"other_direct_income",
	"other_direct_income_rows",
	"management_gross_profit",
	"management_gross_margin_rate",
	"management_gross_profit_display",
	"management_gross_margin_rate_display",
	"tax_estimate_status",
	"tax_estimate_summary",
	"after_estimated_business_tax_profit_preview",
	"excluded_from_15_1_tax_base",
	"excluded_from_management_profit",
	"summary_cards",
	"validations",
	"warnings",
	"blocking_errors",
)


class VehicleManagementProfitSummaryService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, vehicle_name=None, sales_invoice=None):
		vehicle = self._resolve_target_vehicle(vehicle_name=vehicle_name, sales_invoice=sales_invoice)
		if not vehicle:
			self._block("找不到符合條件的單車管理損益 target。")
			self._set_status()
			return self.report

		invoice = self._resolve_invoice(vehicle, sales_invoice=sales_invoice)
		self._read_vehicle(vehicle)
		self._read_invoice(invoice)
		self._resolve_purchase_price(vehicle)
		self._resolve_sale_price(vehicle, invoice)
		self._read_direct_costs(vehicle)
		self._read_other_direct_income(vehicle)
		self._calculate_management_profit()
		self._read_tax_estimate(vehicle, invoice)
		self._build_summary_cards()
		self._set_status()
		return self.report

	def find_candidates(self, limit=10):
		return _get_vehicle_management_profit_summary_candidates(limit=limit)

	def _new_report(self):
		list_keys = {
			"direct_cost_rows",
			"other_direct_income_rows",
			"unmapped_cost_categories",
			"summary_cards",
			"validations",
			"warnings",
			"blocking_errors",
		}
		return {key: [] if key in list_keys else None for key in REPORT_KEYS} | {
			"status": "fail",
			"ready_for_vehicle_page": False,
			"direct_cost_total": 0,
			"cost_breakdown": {},
			"other_direct_income": 0,
			"excluded_from_15_1_tax_base": list(EXCLUDED_FROM_15_1_TAX_BASE),
			"excluded_from_management_profit": list(EXCLUDED_FROM_MANAGEMENT_PROFIT),
		}

	def _resolve_target_vehicle(self, vehicle_name=None, sales_invoice=None):
		if vehicle_name:
			self.report["vehicle"] = vehicle_name
			return frappe.get_doc("Used Car Vehicle", vehicle_name) if frappe.db.exists("Used Car Vehicle", vehicle_name) else None
		if sales_invoice:
			self.report["sales_invoice"] = sales_invoice
			if not frappe.db.exists("Sales Invoice", sales_invoice) or _is_qa_sales_invoice(sales_invoice):
				return None
			vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": sales_invoice}, "name")
			if not vehicle_name:
				vehicle_name = self._resolve_vehicle_from_invoice_items(sales_invoice)
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
		if _is_qa_sales_invoice(invoice_name):
			self._block("Sales Invoice 是 QA draft，不可作為管理損益 target。")
			return None
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		if int(getattr(invoice, "docstatus", 0) or 0) not in (0, 1):
			self._block("Sales Invoice docstatus 必須是 0 或 1。")
		return invoice

	def _resolve_vehicle_from_invoice_items(self, sales_invoice):
		invoice = frappe.get_doc("Sales Invoice", sales_invoice)
		for item in getattr(invoice, "items", []) or []:
			item_code = item.get("item_code") if hasattr(item, "get") else getattr(item, "item_code", None)
			if not item_code:
				continue
			vehicle_name = frappe.db.get_value("Used Car Vehicle", {"item": item_code}, "name")
			if vehicle_name:
				self._warn("Used Car Vehicle.sales_invoice 未連結，已用 Sales Invoice item 反查 Vehicle 作 read-only summary。")
				return vehicle_name
		return None

	def _read_vehicle(self, vehicle):
		self.report.update({"vehicle": vehicle.get("name"), "vehicle_status": vehicle.get("status")})

	def _read_invoice(self, invoice):
		if invoice:
			self.report["sales_invoice_docstatus"] = int(getattr(invoice, "docstatus", 0) or 0)

	def _resolve_purchase_price(self, vehicle):
		purchase_price = flt(vehicle.get("purchase_price"))
		self.report["purchase_price"] = purchase_price
		self.report["purchase_price_source"] = "used_car_vehicle_purchase_price"
		if purchase_price > 0:
			self._validate("purchase_price 來自 Used Car Vehicle.purchase_price，未從 Vehicle Cost 反推。")
		elif vehicle.get("status") == "已售出":
			self._block("已售出車輛缺少 purchase_price；不可從 Vehicle Cost 反推購車價。")
		else:
			self._warn("車輛缺少 purchase_price；不可從 Vehicle Cost 反推購車價。")

	def _resolve_sale_price(self, vehicle, invoice):
		vehicle_sold_price = flt(vehicle.get("sold_price"))
		invoice_grand_total = flt(getattr(invoice, "grand_total", 0)) if invoice and int(getattr(invoice, "docstatus", 0) or 0) in (0, 1) else 0
		if vehicle_sold_price > 0 and invoice_grand_total > 0 and abs(vehicle_sold_price - invoice_grand_total) > ROUNDING_TOLERANCE:
			self._warn("Vehicle.sold_price 與 Sales Invoice grand_total 不一致。")
			if int(getattr(invoice, "docstatus", 0) or 0) == 1:
				self.report["sale_price"] = invoice_grand_total
				self.report["sale_price_source"] = "sales_invoice_grand_total"
			else:
				self.report["sale_price"] = vehicle_sold_price
				self.report["sale_price_source"] = "used_car_vehicle_sold_price"
		elif vehicle_sold_price > 0:
			self.report["sale_price"] = vehicle_sold_price
			self.report["sale_price_source"] = "used_car_vehicle_sold_price"
		elif invoice_grand_total > 0:
			self.report["sale_price"] = invoice_grand_total
			self.report["sale_price_source"] = "sales_invoice_grand_total"
		else:
			self.report["sale_price"] = 0
			self._warn("車輛尚未售出，管理毛利尚不可完整計算。")

	def _read_direct_costs(self, vehicle):
		rows = frappe.db.get_all(
			"Used Car Vehicle Cost",
			filters={"vehicle": vehicle.name},
			fields=("name", "cost_category", "amount", "capitalization_mode", "cost_date"),
			order_by="modified desc",
		)
		breakdown = {}
		unmapped = set()
		for row in rows:
			category = row.get("cost_category") or "其他"
			amount = flt(row.get("amount"))
			if category in PURCHASE_COST_CATEGORIES:
				self._warn("Vehicle Cost 中出現購車價類型，已排除以避免重複扣 purchase_price。")
				continue
			if row.get("capitalization_mode") in ("不列入成本", "代收代付"):
				continue
			mapped_category = DIRECT_COST_CATEGORY_MAP.get(category, "其他直接支出")
			if mapped_category == "其他直接支出" and category not in {"其他", "板金", "烤漆", "拖車", "零件", "工資"}:
				unmapped.add(category)
			self.report["direct_cost_rows"].append(
				{"name": row.get("name"), "cost_category": category, "mapped_category": mapped_category, "amount": amount}
			)
			breakdown[mapped_category] = round(flt(breakdown.get(mapped_category)) + amount, 2)
		self.report["cost_breakdown"] = breakdown
		self.report["unmapped_cost_categories"] = sorted(unmapped)
		self.report["direct_cost_total"] = round(sum(flt(row.get("amount")) for row in self.report["direct_cost_rows"]), 2)

	def _read_other_direct_income(self, vehicle):
		rows = frappe.db.get_all(
			"Used Car Money Flow",
			filters={"vehicle": vehicle.name, "direction": "收入"},
			fields=("name", "flow_type", "direction", "amount", "status", "payment_date"),
			order_by="modified desc",
		)
		for row in rows:
			flow_type = row.get("flow_type")
			if flow_type in SALE_COLLECTION_FLOW_TYPES:
				continue
			if flow_type not in OTHER_INCOME_FLOW_TYPES:
				continue
			amount = flt(row.get("amount"))
			self.report["other_direct_income_rows"].append(
				{"name": row.get("name"), "flow_type": flow_type, "amount": amount, "status": row.get("status")}
			)
		self.report["other_direct_income"] = round(sum(flt(row.get("amount")) for row in self.report["other_direct_income_rows"]), 2)

	def _calculate_management_profit(self):
		if self.report["blocking_errors"]:
			return
		if flt(self.report.get("sale_price")) <= 0:
			self.report["management_gross_profit"] = None
			self.report["management_gross_margin_rate"] = None
			self.report["management_gross_profit_display"] = "尚不可計算"
			self.report["management_gross_margin_rate_display"] = "尚不可計算"
			return
		profit = flt(self.report.get("sale_price")) + flt(self.report.get("other_direct_income")) - flt(self.report.get("purchase_price")) - flt(self.report.get("direct_cost_total"))
		margin = profit / flt(self.report.get("sale_price"))
		self.report["management_gross_profit"] = round(profit, 2)
		self.report["management_gross_margin_rate"] = round(margin, 6)
		self.report["management_gross_profit_display"] = round(profit)
		self.report["management_gross_margin_rate_display"] = f"{margin * 100:.2f}%"

	def _read_tax_estimate(self, vehicle, invoice):
		try:
			tax_report = Vehicle151TaxEstimateService().run(vehicle_name=vehicle.name, sales_invoice=getattr(invoice, "name", None))
		except Exception as exc:
			self.report["tax_estimate_status"] = "warning"
			self.report["tax_estimate_summary"] = {"status": "warning", "message": str(exc)}
			return
		self.report["tax_estimate_status"] = tax_report.get("status")
		self.report["tax_estimate_summary"] = {
			"status": tax_report.get("status"),
			"sale_price": tax_report.get("sale_price"),
			"purchase_price": tax_report.get("purchase_price"),
			"allowed_deduction_raw": tax_report.get("allowed_deduction_raw"),
			"estimated_business_tax_raw": tax_report.get("estimated_business_tax_raw"),
			"excluded_cost_categories": tax_report.get("excluded_cost_categories"),
		}
		if self.report.get("management_gross_profit") is not None and tax_report.get("estimated_business_tax_raw") is not None:
			self.report["after_estimated_business_tax_profit_preview"] = round(
				flt(self.report.get("management_gross_profit")) - flt(tax_report.get("estimated_business_tax_raw")), 2
			)

	def _build_summary_cards(self):
		self.report["summary_cards"] = [
			{"label": "成交價", "amount": self.report.get("sale_price")},
			{"label": "購車價", "amount": self.report.get("purchase_price")},
			{"label": "直接成本", "amount": self.report.get("direct_cost_total")},
			{"label": "管理毛利", "amount": self.report.get("management_gross_profit")},
			{"label": "管理毛利率", "value": self.report.get("management_gross_margin_rate_display")},
		]

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


def _get_vehicle_management_profit_summary_candidates(limit=10):
	vehicles = frappe.db.get_all(
		"Used Car Vehicle",
		filters={"status": ["in", ["已售出", "保留中", "庫存中"]], "purchase_price": [">", 0]},
		fields=("name", "status", "purchase_price", "sold_price", "sales_invoice", "modified"),
		order_by="modified desc",
		limit=limit,
	)
	results = []
	for vehicle in vehicles:
		if not vehicle.get("sold_price") and not vehicle.get("sales_invoice"):
			continue
		invoice_name = vehicle.get("sales_invoice")
		if invoice_name and (not frappe.db.exists("Sales Invoice", invoice_name) or _is_qa_sales_invoice(invoice_name)):
			continue
		results.append(
			{
				"vehicle": vehicle.get("name"),
				"vehicle_status": vehicle.get("status"),
				"purchase_price": flt(vehicle.get("purchase_price")),
				"sold_price": flt(vehicle.get("sold_price")),
				"sales_invoice": invoice_name,
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
def run_vehicle_management_profit_summary(vehicle_name=None, sales_invoice=None):
	return VehicleManagementProfitSummaryService().run(vehicle_name=vehicle_name, sales_invoice=sales_invoice)


@frappe.whitelist()
def find_vehicle_management_profit_summary_candidates(limit=10):
	return VehicleManagementProfitSummaryService().find_candidates(limit=limit)
