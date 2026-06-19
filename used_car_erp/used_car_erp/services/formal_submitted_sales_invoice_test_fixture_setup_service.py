import frappe

from used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service import (
	FormalSalesInvoiceDraftReadinessService,
)
from used_car_erp.used_car_erp.services.guarded_formal_sales_invoice_draft_creation_qa_service import (
	GuardedFormalSalesInvoiceDraftCreationQAService,
)
from used_car_erp.used_car_erp.services.submitted_sales_invoice_submit_gate_snapshot_service import (
	SubmittedSalesInvoiceSubmitGateSnapshotService,
)
from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService
from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService
from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


EXPECTED_SITE = "erpnext-coa.test"
FIXTURE_MARKER = "P1-ACC-6F-C FORMAL SUBMIT FIXTURE"
FIXTURE_KEY = "P1-ACC-6F-C"

REPORT_KEYS = (
	"status",
	"created_fixture",
	"ready_for_submit_test",
	"fixture_marker",
	"site",
	"vehicle",
	"stock_no",
	"item",
	"serial_no",
	"stock_entry",
	"reservation",
	"customer",
	"deposit_money_flow",
	"deposit_voucher_draft",
	"deposit_journal_entry",
	"final_money_flow",
	"final_voucher_draft",
	"final_journal_entry",
	"sales_invoice",
	"sales_invoice_docstatus",
	"readiness_status",
	"readiness_report",
	"draft_creation_status",
	"draft_creation_report",
	"snapshot_status",
	"snapshot_report",
	"counts_before",
	"counts_after",
	"created_documents",
	"validations",
	"warnings",
	"blocking_errors",
)

COUNT_DOCTYPES = (
	"Sales Invoice",
	"Sales Invoice docstatus=1",
	"GL Entry",
	"Stock Ledger Entry",
	"Payment Entry",
	"Journal Entry",
	"Delivery Note",
	"Stock Entry",
	"Used Car Vehicle",
	"Used Car Reservation",
	"Used Car Money Flow",
	"Used Car Voucher Draft",
)


class FormalSubmittedSalesInvoiceTestFixtureSetupService:
	def __init__(self):
		self.report = self._new_report()

	def run(self):
		self.report["site"] = self._site()
		self.report["counts_before"] = self._read_counts()

		if self.report["site"] != EXPECTED_SITE:
			self._block(f"此 fixture setup 只能在 {EXPECTED_SITE} 執行，目前站台是 {self.report['site']}。")
			self._set_status("blocked")
			return self.report

		if self._submitted_sales_invoice_count() > 0:
			self._block("submitted Sales Invoice count 已大於 0，不可建立第一張 submitted Sales Invoice 測試 fixture。")
			self._set_status("blocked")
			return self.report

		existing = find_existing_formal_submit_fixture()
		if existing.get("sales_invoice"):
			self._apply_existing_fixture(existing)
			self._run_snapshot(existing.get("sales_invoice"))
			self.report["created_fixture"] = False
			self._set_status_from_snapshot(existing=True)
			return self.report

		if existing.get("vehicle"):
			self._apply_existing_fixture(existing)
			self.report["validations"].append("已找到既有 formal submit fixture 車輛，但尚未建立 Draft Sales Invoice。")
			self._block("已找到半套 formal submit fixture，但沒有可重用的 Draft Sales Invoice；本 service 不硬刪、不硬修、不重建。")
			self._set_status("fail")
			return self.report

		try:
			self._create_fixture_flow()
		except Exception as exc:
			self._block(f"建立 formal submit fixture 中途失敗：{exc}")
			self.report["counts_after"] = self._read_counts()
			self._set_status("fail")
			return self.report

		self.report["counts_after"] = self._read_counts()
		self._set_status_from_snapshot(existing=False)
		return self.report

	def _new_report(self):
		return {key: [] if key in {"created_documents", "validations", "warnings", "blocking_errors"} else None for key in REPORT_KEYS} | {
			"status": "fail",
			"created_fixture": False,
			"ready_for_submit_test": False,
			"fixture_marker": FIXTURE_MARKER,
		}

	def _site(self):
		return getattr(getattr(frappe, "local", None), "site", None)

	def _read_counts(self):
		counts = {}
		for doctype in COUNT_DOCTYPES:
			if doctype == "Sales Invoice docstatus=1":
				counts[doctype] = frappe.db.count("Sales Invoice", {"docstatus": 1})
			else:
				counts[doctype] = frappe.db.count(doctype)
		return counts

	def _submitted_sales_invoice_count(self):
		return frappe.db.count("Sales Invoice", {"docstatus": 1})

	def _create_fixture_flow(self):
		vehicle = self._create_vehicle()
		self._record_vehicle(vehicle)
		self._record_created("Used Car Vehicle", vehicle.name)

		intake = VehicleIntakeService().complete_intake(vehicle.name)
		self._record_from_result(intake)
		self._record_created("Stock Entry", intake.get("stock_entry"))

		VehicleListingService().list_vehicle(vehicle.name)
		reservation = VehicleReservationService()
		reservation_result = reservation.create_reservation(
			vehicle_name=vehicle.name,
			customer_name="P1 ACC 6F C QA Customer",
			customer_phone="0900000000",
			deposit_amount=10000,
			payment_method="現金",
			payment_reference=FIXTURE_MARKER,
			notes=FIXTURE_MARKER,
		)
		self._record_reservation_result(reservation_result, prefix="deposit")
		self._record_created("Used Car Reservation", reservation_result.get("reservation"))
		self._record_created("Used Car Money Flow", reservation_result.get("money_flow"))
		self._record_created("Used Car Voucher Draft", reservation_result.get("voucher_draft"))

		deposit_confirm = VehicleVoucherService().confirm_voucher_draft(reservation_result.get("voucher_draft"), FIXTURE_MARKER)
		self.report["deposit_journal_entry"] = deposit_confirm.get("journal_entry")
		self._record_created("Journal Entry", deposit_confirm.get("journal_entry"))

		final_result = reservation.create_final_payment_for_active_reservation(
			vehicle_name=vehicle.name,
			amount=990000,
			payment_method="現金",
			payment_reference=FIXTURE_MARKER,
			notes=FIXTURE_MARKER,
		)
		self._record_reservation_result(final_result, prefix="final")
		self._record_created("Used Car Money Flow", final_result.get("money_flow"))
		self._record_created("Used Car Voucher Draft", final_result.get("voucher_draft"))

		final_confirm = VehicleVoucherService().confirm_voucher_draft(final_result.get("voucher_draft"), FIXTURE_MARKER)
		self.report["final_journal_entry"] = final_confirm.get("journal_entry")
		self._record_created("Journal Entry", final_confirm.get("journal_entry"))

		preflight = reservation.preflight_delivery_for_active_reservation(vehicle.name)
		self._record_reservation_result(preflight, prefix="both")
		reservation.complete_active_reservation(vehicle.name, completion_note=FIXTURE_MARKER)

		readiness = FormalSalesInvoiceDraftReadinessService().run(vehicle.name)
		self.report["readiness_report"] = readiness
		self.report["readiness_status"] = readiness.get("status")
		if readiness.get("status") != "pass" or readiness.get("ready_to_create_sales_invoice_draft") is not True:
			self._block("readiness 未通過，不建立 Sales Invoice draft。")
			return

		draft = GuardedFormalSalesInvoiceDraftCreationQAService().run(vehicle_name=vehicle.name, note=FIXTURE_MARKER)
		self.report["draft_creation_report"] = draft
		self.report["draft_creation_status"] = draft.get("status")
		self.report["sales_invoice"] = draft.get("sales_invoice")
		self.report["sales_invoice_docstatus"] = draft.get("sales_invoice_docstatus")
		if draft.get("sales_invoice"):
			self._record_created("Sales Invoice", draft.get("sales_invoice"))
		if not draft.get("created") or not draft.get("sales_invoice"):
			self._block("guarded draft creation 未建立 Sales Invoice draft。")
			return

		self._mark_sales_invoice(draft.get("sales_invoice"))
		self.report["created_fixture"] = True
		self._run_snapshot(draft.get("sales_invoice"))

	def _create_vehicle(self):
		suffix = frappe.generate_hash(length=8)
		meta = frappe.get_meta("Used Car Vehicle")
		values = {
			"doctype": "Used Car Vehicle",
			"brand": "Toyota",
			"model": "Altis",
			"year": 2020,
			"license_plate": f"{FIXTURE_KEY}-{suffix[:4]}",
			"vin": f"{FIXTURE_KEY}-{suffix}",
			"purchase_price": 300000,
		}
		for fieldname, value in (
			("purchase_source_type", "個人"),
			("purchase_document_type", "買賣合約"),
			("notes", FIXTURE_MARKER),
			("tax_review_note", FIXTURE_MARKER),
			("purchase_note", FIXTURE_MARKER),
		):
			if meta.has_field(fieldname):
				values[fieldname] = value
		return frappe.get_doc(values).insert()

	def _record_vehicle(self, vehicle):
		self.report["vehicle"] = vehicle.name
		self.report["stock_no"] = vehicle.get("stock_no")

	def _record_from_result(self, result):
		for key in ("item", "serial_no", "stock_entry", "stock_no"):
			if result.get(key):
				self.report[key] = result.get(key)

	def _record_reservation_result(self, result, prefix):
		if result.get("reservation"):
			self.report["reservation"] = result.get("reservation")
		if result.get("customer"):
			self.report["customer"] = result.get("customer")
		if prefix in {"deposit", "both"}:
			self.report["deposit_money_flow"] = result.get("deposit_money_flow") or result.get("money_flow") or self.report.get("deposit_money_flow")
			self.report["deposit_voucher_draft"] = result.get("deposit_voucher_draft") or result.get("voucher_draft") or self.report.get("deposit_voucher_draft")
			self.report["deposit_journal_entry"] = result.get("deposit_journal_entry") or self.report.get("deposit_journal_entry")
		if prefix in {"final", "both"}:
			self.report["final_money_flow"] = result.get("final_money_flow") or result.get("money_flow") or self.report.get("final_money_flow")
			self.report["final_voucher_draft"] = result.get("final_voucher_draft") or result.get("voucher_draft") or self.report.get("final_voucher_draft")
			self.report["final_journal_entry"] = result.get("final_journal_entry") or self.report.get("final_journal_entry")

	def _run_snapshot(self, sales_invoice):
		snapshot = SubmittedSalesInvoiceSubmitGateSnapshotService().run(sales_invoice=sales_invoice)
		self.report["snapshot_report"] = snapshot
		self.report["snapshot_status"] = snapshot.get("status")
		self.report["ready_for_submit_test"] = snapshot.get("ready_for_submit_test") is True

	def _apply_existing_fixture(self, existing):
		for key in (
			"vehicle",
			"stock_no",
			"item",
			"serial_no",
			"stock_entry",
			"reservation",
			"sales_invoice",
			"sales_invoice_docstatus",
		):
			if existing.get(key) is not None:
				self.report[key] = existing.get(key)
		if existing.get("sales_invoice"):
			self.report["validations"].append("已找到既有 formal submit fixture draft，未重複建立資料。")

	def _record_created(self, doctype, name):
		if name:
			self.report["created_documents"].append({"doctype": doctype, "name": name})

	def _mark_sales_invoice(self, sales_invoice):
		if not sales_invoice or not frappe.db.exists("Sales Invoice", sales_invoice):
			return
		invoice = frappe.get_doc("Sales Invoice", sales_invoice)
		if int(getattr(invoice, "docstatus", 0) or 0) != 0:
			self._block("Sales Invoice marker 只能寫入 Draft invoice；目前 docstatus 不是 0。")
			return
		remarks = getattr(invoice, "remarks", None) or ""
		if FIXTURE_MARKER in remarks:
			return
		invoice.remarks = "\n".join(part for part in (remarks, FIXTURE_MARKER) if part)
		invoice.save()
		frappe.db.commit()

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _set_status(self, status):
		self.report["status"] = status
		self.report["counts_after"] = self.report.get("counts_after") or self._read_counts()

	def _set_status_from_snapshot(self, existing):
		if self.report["blocking_errors"]:
			self._set_status("warning" if self.report.get("sales_invoice") else "fail")
		elif self.report.get("ready_for_submit_test"):
			self._set_status("pass")
		elif self.report.get("sales_invoice"):
			self._set_status("warning")
		else:
			self._set_status("fail")
		if existing and self.report["status"] == "pass":
			self.report["created_fixture"] = False


def find_existing_formal_submit_fixture():
	vehicle = _find_fixture_vehicle()
	sales_invoice = _find_fixture_sales_invoice(vehicle.get("vehicle") if vehicle else None)
	if not vehicle and sales_invoice:
		vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": sales_invoice}, "name")
		vehicle = _vehicle_payload(vehicle_name) if vehicle_name else None

	result = vehicle or {}
	if sales_invoice:
		result = dict(result)
		result["sales_invoice"] = sales_invoice
		if frappe.db.exists("Sales Invoice", sales_invoice):
			result["sales_invoice_docstatus"] = getattr(frappe.get_doc("Sales Invoice", sales_invoice), "docstatus", None)
	return result


def _find_fixture_vehicle():
	filters_list = [
		{"name": ["like", f"%{FIXTURE_KEY}%"]},
		{"license_plate": ["like", f"%{FIXTURE_KEY}%"]},
		{"vin": ["like", f"%{FIXTURE_KEY}%"]},
		{"notes": ["like", f"%{FIXTURE_KEY}%"]},
		{"tax_review_note": ["like", f"%{FIXTURE_KEY}%"]},
		{"formal_delivery_status": "銷售發票草稿", "sales_invoice": ["is", "set"]},
	]
	for filters in filters_list:
		name = frappe.db.get_value("Used Car Vehicle", filters, "name", order_by="modified desc")
		if name:
			return _vehicle_payload(name)
	return None


def _find_fixture_sales_invoice(vehicle_name=None):
	invoice = frappe.db.get_value(
		"Sales Invoice",
		{"docstatus": 0, "remarks": ["like", f"%{FIXTURE_MARKER}%"]},
		"name",
		order_by="modified desc",
	)
	if invoice:
		return invoice
	if vehicle_name:
		invoice = frappe.db.get_value("Used Car Vehicle", vehicle_name, "sales_invoice")
		if invoice and frappe.db.exists("Sales Invoice", invoice):
			invoice_docstatus = getattr(frappe.get_doc("Sales Invoice", invoice), "docstatus", None)
			if int(invoice_docstatus or 0) == 0:
				return invoice
	return None


def _vehicle_payload(vehicle_name):
	if not vehicle_name or not frappe.db.exists("Used Car Vehicle", vehicle_name):
		return None
	vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
	return {
		"vehicle": vehicle.name,
		"stock_no": vehicle.get("stock_no"),
		"item": vehicle.get("item"),
		"serial_no": vehicle.get("serial_no"),
		"stock_entry": vehicle.get("stock_entry"),
		"reservation": vehicle.get("completed_reservation"),
		"sales_invoice": vehicle.get("sales_invoice"),
	}


@frappe.whitelist()
def run_formal_submitted_sales_invoice_test_fixture_setup():
	return FormalSubmittedSalesInvoiceTestFixtureSetupService().run()
