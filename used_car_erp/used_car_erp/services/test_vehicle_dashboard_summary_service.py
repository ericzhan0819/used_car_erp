from used_car_erp.used_car_erp.services import vehicle_dashboard_summary_service as service


class FakeSummaryService:
	def __init__(self, report=None, candidates=None, error=None):
		self.report = report or {}
		self.candidates = candidates or []
		self.error = error
		self.calls = []

	def run(self, vehicle_name=None, sales_invoice=None):
		self.calls.append(("run", vehicle_name, sales_invoice))
		if self.error:
			raise self.error
		return dict(self.report)

	def find_candidates(self, limit=10):
		self.calls.append(("find_candidates", limit))
		if self.error:
			raise self.error
		return list(self.candidates)[: int(limit or 10)]

	def insert(self):
		raise AssertionError("insert must not be called")

	def save(self):
		raise AssertionError("save must not be called")

	def submit(self):
		raise AssertionError("submit must not be called")

	def cancel(self):
		raise AssertionError("cancel must not be called")

	def db_set(self, *args, **kwargs):
		raise AssertionError("db_set must not be called")


def _default_reports():
	return {
		"accounting": {
			"status": "pass",
			"ready_for_vehicle_page": True,
			"vehicle": "UCV-DASH",
			"sales_invoice": "SINV-DASH",
			"business_status": "發票已提交",
			"closed": False,
			"next_action_code": "create_advance_settlement",
			"next_action_label": "建立預收款沖轉",
			"next_action_area": "會計作業",
		},
		"tax": {
			"status": "pass",
			"ready_for_vehicle_page": True,
			"vehicle": "UCV-DASH",
			"sales_invoice": "SINV-DASH",
			"estimate_reliable": True,
			"allowed_deduction_display": 15000,
			"estimated_business_tax_display": 3000,
			"tax_mode_applicability": "15-1 特殊扣抵，適用 15-1 公式估算售車營業稅。",
		},
		"profit": {
			"status": "pass",
			"ready_for_vehicle_page": True,
			"vehicle": "UCV-DASH",
			"sales_invoice": "SINV-DASH",
			"management_gross_profit_display": 44000,
			"management_gross_margin_rate_display": "11.64%",
			"direct_cost_total": 21000,
		},
	}


def _patch_services(monkeypatch, reports=None, errors=None, candidates=None):
	reports = reports or _default_reports()
	errors = errors or {}
	candidates = candidates or {}
	instances = {
		"accounting": FakeSummaryService(
			report=reports.get("accounting"),
			candidates=candidates.get("accounting"),
			error=errors.get("accounting"),
		),
		"tax": FakeSummaryService(
			report=reports.get("tax"),
			candidates=candidates.get("tax"),
			error=errors.get("tax"),
		),
		"profit": FakeSummaryService(
			report=reports.get("profit"),
			candidates=candidates.get("profit"),
			error=errors.get("profit"),
		),
	}
	monkeypatch.setattr(service, "VehicleAccountingStatusSummaryService", lambda: instances["accounting"])
	monkeypatch.setattr(service, "Vehicle151TaxEstimateService", lambda: instances["tax"])
	monkeypatch.setattr(service, "VehicleManagementProfitSummaryService", lambda: instances["profit"])
	return instances


def test_run_returns_single_payload_with_three_summaries(monkeypatch):
	_patch_services(monkeypatch)
	report = service.VehicleDashboardSummaryService().run(vehicle_name="UCV-DASH")
	assert report["status"] == "pass"
	assert report["ready_for_vehicle_page"] is True
	assert report["vehicle"] == "UCV-DASH"
	assert report["sales_invoice"] == "SINV-DASH"
	assert report["service_statuses"] == {
		"accounting_status": "pass",
		"tax_estimate": "pass",
		"management_profit": "pass",
	}
	assert report["accounting_status_summary"]["business_status"] == "發票已提交"
	assert report["tax_estimate_summary"]["estimated_business_tax_display"] == 3000
	assert report["management_profit_summary"]["management_gross_profit_display"] == 44000
	assert list(report.keys()) == list(service.REPORT_KEYS)


def test_vehicle_page_summary_is_thin_consumption_payload(monkeypatch):
	_patch_services(monkeypatch)
	report = service.run_vehicle_dashboard_summary(vehicle_name="UCV-DASH")
	assert report["vehicle_page_summary"] == {
		"accounting": {
			"status": "pass",
			"business_status": "發票已提交",
			"closed": False,
			"next_action_code": "create_advance_settlement",
			"next_action_label": "建立預收款沖轉",
			"next_action_area": "會計作業",
		},
		"tax_15_1": {
			"status": "pass",
			"estimate_reliable": True,
			"allowed_deduction_display": 15000,
			"estimated_business_tax_display": 3000,
			"tax_mode_applicability": "15-1 特殊扣抵，適用 15-1 公式估算售車營業稅。",
		},
		"management_profit": {
			"status": "pass",
			"management_gross_profit_display": 44000,
			"management_gross_margin_rate_display": "11.64%",
			"direct_cost_total": 21000,
		},
	}
	assert [card["label"] for card in report["summary_cards"]] == ["會計狀態", "15-1 稅務估算", "管理損益"]


def test_individual_summary_exception_is_preserved(monkeypatch):
	_patch_services(monkeypatch, errors={"tax": RuntimeError("tax service unavailable")})
	report = service.VehicleDashboardSummaryService().run(vehicle_name="UCV-DASH")
	assert report["status"] == "warning"
	assert report["ready_for_vehicle_page"] is True
	assert report["service_statuses"]["accounting_status"] == "pass"
	assert report["service_statuses"]["tax_estimate"] == "fail"
	assert report["service_statuses"]["management_profit"] == "pass"
	assert report["tax_estimate_summary"] == {
		"status": "fail",
		"message": "tax service unavailable",
		"exception": "RuntimeError",
	}
	assert "tax_estimate summary failed: tax service unavailable" in report["warnings"]


def test_summary_status_failure_does_not_drop_other_summaries(monkeypatch):
	reports = _default_reports()
	reports["tax"] = {
		"status": "fail",
		"ready_for_vehicle_page": False,
		"vehicle": "UCV-DASH",
		"blocking_errors": ["缺少售車價"],
	}
	_patch_services(monkeypatch, reports=reports)
	report = service.VehicleDashboardSummaryService().run(vehicle_name="UCV-DASH")
	assert report["status"] == "warning"
	assert report["service_statuses"]["tax_estimate"] == "fail"
	assert report["accounting_status_summary"]["business_status"] == "發票已提交"
	assert report["management_profit_summary"]["management_gross_profit_display"] == 44000


def test_all_summary_exceptions_make_aggregator_fail(monkeypatch):
	_patch_services(
		monkeypatch,
		errors={
			"accounting": RuntimeError("accounting failed"),
			"tax": RuntimeError("tax failed"),
			"profit": RuntimeError("profit failed"),
		},
	)
	report = service.VehicleDashboardSummaryService().run(vehicle_name="UCV-DASH")
	assert report["status"] == "fail"
	assert report["ready_for_vehicle_page"] is False
	assert report["service_statuses"] == {
		"accounting_status": "fail",
		"tax_estimate": "fail",
		"management_profit": "fail",
	}


def test_find_candidates_merges_source_rows_without_writing(monkeypatch):
	instances = _patch_services(
		monkeypatch,
		candidates={
			"accounting": [
				{"vehicle": "UCV-2", "sales_invoice": "SINV-2", "business_status": "待會計確認"},
				{"vehicle": "UCV-1", "sales_invoice": "SINV-1", "business_status": "發票已提交"},
			],
			"tax": [{"vehicle": "UCV-1", "sales_invoice": "SINV-1", "estimated_business_tax_display": 3000}],
			"profit": [{"vehicle": "UCV-3", "sales_invoice": None, "management_gross_profit_display": 44000}],
		},
	)
	report = service.find_vehicle_dashboard_summary_candidates(limit=10)
	assert report["status"] == "pass"
	assert [row["vehicle"] for row in report["candidates"]] == ["UCV-2", "UCV-1", "UCV-3"]
	assert set(report["candidates"][1]["sources"].keys()) == {"accounting_status", "tax_estimate"}
	assert instances["accounting"].calls == [("find_candidates", 10)]
	assert instances["tax"].calls == [("find_candidates", 10)]
	assert instances["profit"].calls == [("find_candidates", 10)]
	assert list(report.keys()) == list(service.CANDIDATE_REPORT_KEYS)


def test_candidate_source_failure_is_preserved(monkeypatch):
	_patch_services(
		monkeypatch,
		errors={"profit": RuntimeError("profit candidate failed")},
		candidates={
			"accounting": [{"vehicle": "UCV-1", "sales_invoice": "SINV-1"}],
			"tax": [{"vehicle": "UCV-1", "sales_invoice": "SINV-1"}],
		},
	)
	report = service.VehicleDashboardSummaryService().find_candidates(limit=10)
	assert report["status"] == "warning"
	assert report["source_statuses"] == {
		"accounting_status": "pass",
		"tax_estimate": "pass",
		"management_profit": "fail",
	}
	assert report["candidates"][0]["vehicle"] == "UCV-1"
	assert "management_profit candidate finder failed: profit candidate failed" in report["warnings"]
