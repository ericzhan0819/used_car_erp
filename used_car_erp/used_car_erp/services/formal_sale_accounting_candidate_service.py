import frappe
from frappe.utils import flt


CATEGORY_LABELS = {
	"needs_sales_invoice_submit": "待確認銷售發票並出庫",
	"needs_advance_settlement_draft": "待建立預收款沖轉草稿",
	"needs_advance_settlement_submit": "待確認預收款沖轉入帳",
	"blocked": "需補資料 / blocked formal accounting",
	"needs_sales_invoice_recovery": "需技術修復 Sales Invoice 草稿連結",
}

CATEGORY_NEXT_STEPS = {
	"needs_sales_invoice_submit": "確認銷售發票並出庫",
	"needs_advance_settlement_draft": "建立預收款沖轉草稿",
	"needs_advance_settlement_submit": "確認預收款沖轉入帳",
	"blocked": "補齊資料或人工確認正式售車會計狀態",
	"needs_sales_invoice_recovery": "修復 Sales Invoice 草稿連結",
}

CATEGORY_ORDER = (
	"needs_sales_invoice_recovery",
	"blocked",
	"needs_sales_invoice_submit",
	"needs_advance_settlement_draft",
	"needs_advance_settlement_submit",
)

VEHICLE_FIELDS = (
	"name",
	"status",
	"stock_no",
	"license_plate",
	"customer",
	"sold_price",
	"sales_invoice",
	"formal_delivery_status",
	"advance_settlement_journal_entry",
	"modified",
)


class FormalSaleAccountingCandidateService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, limit=50):
		self.report = self._new_report()
		limit = self._normalize_limit(limit)
		vehicles = frappe.db.get_all(
			"Used Car Vehicle",
			filters={"status": "已售出"},
			fields=VEHICLE_FIELDS,
			order_by="modified desc",
			limit=limit,
		)

		for vehicle in vehicles:
			candidate = self._build_candidate(vehicle)
			if candidate:
				self.report["candidates"].append(candidate)
				self.report["category_counts"][candidate["category"]] += 1

		self.report["candidates"].sort(key=lambda row: CATEGORY_ORDER.index(row["category"]))
		self.report["candidate_count"] = len(self.report["candidates"])
		self._set_status()
		return self.report

	def _new_report(self):
		return {
			"status": "fail",
			"candidate_count": 0,
			"candidates": [],
			"category_counts": {category: 0 for category in CATEGORY_ORDER},
			"warnings": [],
			"blocking_errors": [],
		}

	def _normalize_limit(self, limit):
		try:
			limit = int(limit or 50)
		except (TypeError, ValueError):
			self.report["warnings"].append("limit 無法解析，已使用預設 50。")
			limit = 50
		return max(1, min(limit, 500))

	def _build_candidate(self, vehicle):
		invoice = self._load_linked_doc("Sales Invoice", vehicle.get("sales_invoice"), vehicle)
		settlement = self._load_linked_doc("Journal Entry", vehicle.get("advance_settlement_journal_entry"), vehicle)
		category, reasons = self._resolve_category(vehicle, invoice, settlement)
		if not category:
			return None
		return self._candidate_payload(vehicle, invoice, settlement, category, reasons)

	def _load_linked_doc(self, doctype, name, vehicle):
		if not name:
			return None
		if not frappe.db.exists(doctype, name):
			return {"_missing": True, "doctype": doctype, "name": name}
		try:
			return frappe.get_doc(doctype, name)
		except Exception as exc:
			self.report["warnings"].append(f"{doctype} {name} 無法讀取：{exc}")
			return {"_missing": True, "doctype": doctype, "name": name}

	def _resolve_category(self, vehicle, invoice, settlement):
		reasons = []
		invoice_docstatus = _docstatus(invoice)
		settlement_docstatus = _docstatus(settlement)

		if invoice_docstatus == 2:
			return "needs_sales_invoice_recovery", ["Linked Sales Invoice 已取消，需要技術修復草稿連結。"]
		if invoice_docstatus == 1 and settlement_docstatus == 1:
			return None, []

		blocked_reasons = self._blocked_reasons(vehicle, invoice, settlement)
		if blocked_reasons:
			return "blocked", blocked_reasons

		if invoice_docstatus == 0:
			return "needs_sales_invoice_submit", reasons

		if (
			invoice_docstatus == 1
			and vehicle.get("formal_delivery_status") == "已完成"
			and not vehicle.get("advance_settlement_journal_entry")
		):
			return "needs_advance_settlement_draft", reasons

		if settlement_docstatus == 0:
			return "needs_advance_settlement_submit", reasons

		return "blocked", ["已售出車輛的正式售車會計狀態不符合初版候選分類。"]

	def _blocked_reasons(self, vehicle, invoice, settlement):
		reasons = []
		if vehicle.get("status") != "已售出":
			reasons.append("車輛狀態不是已售出。")
		if not vehicle.get("sales_invoice"):
			reasons.append("已售出車輛缺少 Sales Invoice 連結。")
		elif _is_missing_doc(invoice):
			reasons.append(f"Linked Sales Invoice 不存在或無法讀取：{vehicle.get('sales_invoice')}")
		elif _docstatus(invoice) not in (0, 1, 2):
			reasons.append("Linked Sales Invoice docstatus 無法辨識。")
		if vehicle.get("advance_settlement_journal_entry"):
			if _is_missing_doc(settlement):
				reasons.append(f"Linked Journal Entry 不存在或無法讀取：{vehicle.get('advance_settlement_journal_entry')}")
			elif _docstatus(settlement) not in (0, 1, 2):
				reasons.append("Linked Journal Entry docstatus 無法辨識。")
			elif _docstatus(settlement) == 2:
				reasons.append("Linked Journal Entry 已取消。")
		return reasons

	def _candidate_payload(self, vehicle, invoice, settlement, category, blocking_reasons):
		route_doctype, route_name = self._route(vehicle, invoice, settlement, category)
		return {
			"category": category,
			"category_label": CATEGORY_LABELS[category],
			"vehicle": vehicle.get("name"),
			"vehicle_status": vehicle.get("status"),
			"modified": vehicle.get("modified"),
			"stock_no": vehicle.get("stock_no"),
			"license_plate": vehicle.get("license_plate"),
			"customer": self._customer(vehicle, invoice),
			"sold_price": flt(vehicle.get("sold_price")),
			"sales_invoice": vehicle.get("sales_invoice"),
			"sales_invoice_docstatus": _docstatus(invoice),
			"sales_invoice_status": _get_doc_value(invoice, "status"),
			"advance_settlement_journal_entry": vehicle.get("advance_settlement_journal_entry"),
			"advance_settlement_journal_entry_docstatus": _docstatus(settlement),
			"next_step": CATEGORY_NEXT_STEPS[category],
			"route_doctype": route_doctype,
			"route_name": route_name,
			"secondary_routes": self._secondary_routes(vehicle, invoice, settlement, route_doctype, route_name),
			"blocking_reasons": blocking_reasons if category == "blocked" else [],
			"warnings": blocking_reasons if category == "needs_sales_invoice_recovery" else [],
		}

	def _route(self, vehicle, invoice, settlement, category):
		if category == "needs_sales_invoice_submit" and not _is_missing_doc(invoice):
			return "Sales Invoice", _get_doc_value(invoice, "name") or vehicle.get("sales_invoice")
		if category == "needs_advance_settlement_submit" and not _is_missing_doc(settlement):
			return "Journal Entry", _get_doc_value(settlement, "name") or vehicle.get("advance_settlement_journal_entry")
		return "Used Car Vehicle", vehicle.get("name")

	def _secondary_routes(self, vehicle, invoice, settlement, route_doctype, route_name):
		routes = []
		for doctype, name in (
			("Used Car Vehicle", vehicle.get("name")),
			("Sales Invoice", vehicle.get("sales_invoice")),
			("Journal Entry", vehicle.get("advance_settlement_journal_entry")),
		):
			if not name or (doctype == route_doctype and name == route_name):
				continue
			if doctype == "Sales Invoice" and _is_missing_doc(invoice):
				continue
			if doctype == "Journal Entry" and _is_missing_doc(settlement):
				continue
			routes.append({"doctype": doctype, "name": name})
		return routes

	def _customer(self, vehicle, invoice):
		return vehicle.get("customer") or _get_doc_value(invoice, "customer")

	def _set_status(self):
		if self.report["blocking_errors"]:
			self.report["status"] = "fail"
		elif self.report["warnings"]:
			self.report["status"] = "partial"
		else:
			self.report["status"] = "pass"


def _is_missing_doc(doc):
	return isinstance(doc, dict) and doc.get("_missing") is True


def _docstatus(doc):
	if not doc or _is_missing_doc(doc):
		return None
	return int(_get_doc_value(doc, "docstatus") or 0)


def _get_doc_value(doc, key):
	if not doc or _is_missing_doc(doc):
		return None
	if hasattr(doc, "get"):
		return doc.get(key)
	return getattr(doc, key, None)


@frappe.whitelist()
def run_formal_sale_accounting_candidates(limit=50):
	return FormalSaleAccountingCandidateService().run(limit=limit)
