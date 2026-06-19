import frappe

from used_car_erp.used_car_erp.services.vehicle_15_1_tax_estimate_service import Vehicle151TaxEstimateService
from used_car_erp.used_car_erp.services.vehicle_accounting_status_summary_service import VehicleAccountingStatusSummaryService
from used_car_erp.used_car_erp.services.vehicle_management_profit_summary_service import VehicleManagementProfitSummaryService


REPORT_KEYS = (
	"status",
	"ready_for_vehicle_page",
	"vehicle",
	"sales_invoice",
	"service_statuses",
	"accounting_status_summary",
	"tax_estimate_summary",
	"management_profit_summary",
	"vehicle_page_summary",
	"summary_cards",
	"warnings",
	"blocking_errors",
)

CANDIDATE_REPORT_KEYS = (
	"status",
	"limit",
	"source_statuses",
	"candidates",
	"warnings",
	"blocking_errors",
)


class VehicleDashboardSummaryService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, vehicle_name=None, sales_invoice=None):
		self.report = self._new_report()
		self.report["vehicle"] = vehicle_name
		self.report["sales_invoice"] = sales_invoice

		for service_key, summary_key, service_factory in self._summary_services():
			self._run_summary(service_key, summary_key, service_factory, vehicle_name=vehicle_name, sales_invoice=sales_invoice)

		self._build_vehicle_page_summary()
		self._build_summary_cards()
		self._set_status()
		return self.report

	def find_candidates(self, limit=10):
		limit = int(limit or 10)
		report = self._new_candidate_report(limit=limit)
		merged = {}
		ordered_keys = []

		for service_key, _summary_key, service_factory in self._summary_services():
			try:
				rows = service_factory().find_candidates(limit=limit) or []
			except Exception as exc:
				report["source_statuses"][service_key] = "fail"
				report["warnings"].append(f"{service_key} candidate finder failed: {exc}")
				continue

			report["source_statuses"][service_key] = "pass"
			for row in rows:
				key = row.get("vehicle") or row.get("sales_invoice")
				if not key:
					continue
				if key not in merged:
					ordered_keys.append(key)
					merged[key] = {
						"vehicle": row.get("vehicle"),
						"sales_invoice": row.get("sales_invoice"),
						"sources": {},
					}
				merged[key]["vehicle"] = merged[key].get("vehicle") or row.get("vehicle")
				merged[key]["sales_invoice"] = merged[key].get("sales_invoice") or row.get("sales_invoice")
				merged[key]["sources"][service_key] = row

		report["candidates"] = [merged[key] for key in ordered_keys[:limit]]
		self._set_candidate_status(report)
		return report

	def _summary_services(self):
		return (
			("accounting_status", "accounting_status_summary", VehicleAccountingStatusSummaryService),
			("tax_estimate", "tax_estimate_summary", Vehicle151TaxEstimateService),
			("management_profit", "management_profit_summary", VehicleManagementProfitSummaryService),
		)

	def _new_report(self):
		return {key: [] if key in {"summary_cards", "warnings", "blocking_errors"} else None for key in REPORT_KEYS} | {
			"status": "fail",
			"ready_for_vehicle_page": False,
			"service_statuses": {},
			"vehicle_page_summary": {},
		}

	def _new_candidate_report(self, limit=10):
		return {key: [] if key in {"candidates", "warnings", "blocking_errors"} else None for key in CANDIDATE_REPORT_KEYS} | {
			"status": "fail",
			"limit": limit,
			"source_statuses": {},
		}

	def _run_summary(self, service_key, summary_key, service_factory, vehicle_name=None, sales_invoice=None):
		try:
			summary = service_factory().run(vehicle_name=vehicle_name, sales_invoice=sales_invoice) or {}
		except Exception as exc:
			summary = {"status": "fail", "message": str(exc), "exception": exc.__class__.__name__}
			self.report["warnings"].append(f"{service_key} summary failed: {exc}")

		self.report[summary_key] = summary
		self.report["service_statuses"][service_key] = summary.get("status") or "unknown"
		self._sync_target_from_summary(summary)

	def _sync_target_from_summary(self, summary):
		if not self.report.get("vehicle") and summary.get("vehicle"):
			self.report["vehicle"] = summary.get("vehicle")
		if not self.report.get("sales_invoice") and summary.get("sales_invoice"):
			self.report["sales_invoice"] = summary.get("sales_invoice")

	def _build_vehicle_page_summary(self):
		accounting = self.report.get("accounting_status_summary") or {}
		tax = self.report.get("tax_estimate_summary") or {}
		profit = self.report.get("management_profit_summary") or {}
		self.report["vehicle_page_summary"] = {
			"accounting": {
				"status": accounting.get("status"),
				"business_status": accounting.get("business_status"),
				"closed": accounting.get("closed"),
				"next_action_code": accounting.get("next_action_code"),
				"next_action_label": accounting.get("next_action_label"),
				"next_action_area": accounting.get("next_action_area"),
			},
			"tax_15_1": {
				"status": tax.get("status"),
				"estimate_reliable": tax.get("estimate_reliable"),
				"allowed_deduction_display": tax.get("allowed_deduction_display"),
				"estimated_business_tax_display": tax.get("estimated_business_tax_display"),
				"tax_mode_applicability": tax.get("tax_mode_applicability"),
			},
			"management_profit": {
				"status": profit.get("status"),
				"management_gross_profit_display": profit.get("management_gross_profit_display"),
				"management_gross_margin_rate_display": profit.get("management_gross_margin_rate_display"),
				"direct_cost_total": profit.get("direct_cost_total"),
			},
		}

	def _build_summary_cards(self):
		vehicle_page_summary = self.report.get("vehicle_page_summary") or {}
		accounting = vehicle_page_summary.get("accounting") or {}
		tax = vehicle_page_summary.get("tax_15_1") or {}
		profit = vehicle_page_summary.get("management_profit") or {}
		self.report["summary_cards"] = [
			{
				"area": "accounting",
				"label": "會計狀態",
				"status": accounting.get("status"),
				"value": accounting.get("business_status"),
				"next_action_label": accounting.get("next_action_label"),
				"next_action_area": accounting.get("next_action_area"),
			},
			{
				"area": "tax_15_1",
				"label": "15-1 稅務估算",
				"status": tax.get("status"),
				"allowed_deduction_display": tax.get("allowed_deduction_display"),
				"estimated_business_tax_display": tax.get("estimated_business_tax_display"),
			},
			{
				"area": "management_profit",
				"label": "管理損益",
				"status": profit.get("status"),
				"management_gross_profit_display": profit.get("management_gross_profit_display"),
				"management_gross_margin_rate_display": profit.get("management_gross_margin_rate_display"),
			},
		]

	def _set_status(self):
		statuses = list((self.report.get("service_statuses") or {}).values())
		summaries = [
			self.report.get("accounting_status_summary") or {},
			self.report.get("tax_estimate_summary") or {},
			self.report.get("management_profit_summary") or {},
		]
		self.report["ready_for_vehicle_page"] = any(bool(summary.get("ready_for_vehicle_page")) for summary in summaries)
		if not statuses or all(status == "fail" for status in statuses):
			self.report["status"] = "fail"
		elif any(status in ("fail", "warning", "unknown") for status in statuses) or self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"

	def _set_candidate_status(self, report):
		statuses = list((report.get("source_statuses") or {}).values())
		if not statuses or all(status == "fail" for status in statuses):
			report["status"] = "fail"
		elif any(status != "pass" for status in statuses) or report["warnings"]:
			report["status"] = "warning"
		else:
			report["status"] = "pass"


@frappe.whitelist()
def run_vehicle_dashboard_summary(vehicle_name=None, sales_invoice=None):
	return VehicleDashboardSummaryService().run(vehicle_name=vehicle_name, sales_invoice=sales_invoice)


@frappe.whitelist()
def find_vehicle_dashboard_summary_candidates(limit=10):
	return VehicleDashboardSummaryService().find_candidates(limit=limit)
