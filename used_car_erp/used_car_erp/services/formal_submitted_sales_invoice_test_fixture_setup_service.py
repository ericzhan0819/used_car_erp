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
from used_car_erp.used_car_erp.services.vehicle_stock_service import VehicleStockService
from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


EXPECTED_SITE = "erpnext-coa.test"
FIXTURE_MARKER = "P1-ACC-6F-C FORMAL SUBMIT FIXTURE"
FIXTURE_KEY = "P1-ACC-6F-C"

REPORT_KEYS = (
	"status",
	"created_fixture",
	"ready_for_submit_test",
	"resume_mode",
	"resume_stage",
	"resume_state",
	"existing_fixture",
	"fixture_marker",
	"site",
	"vehicle",
	"stock_no",
	"item",
	"serial_no",
	"stock_entry",
	"stock_adjustment_account",
	"stock_entry_difference_account",
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
			self.report["resume_mode"] = "existing_draft"
			self.report["resume_stage"] = "snapshot_pass"
			self.report["existing_fixture"] = existing
			self._apply_existing_fixture(existing)
			if not self._validate_existing_sales_invoice(existing.get("sales_invoice")):
				self._set_status("fail")
				return self.report
			self._run_snapshot(existing.get("sales_invoice"))
			self.report["created_fixture"] = False
			self._set_status_from_snapshot(existing=True)
			return self.report

		if existing.get("vehicle"):
			self.report["resume_mode"] = "half_fixture_resume"
			self.report["existing_fixture"] = existing
			try:
				self._resume_existing_fixture_flow(existing)
			except Exception as exc:
				self._block(f"續跑 formal submit fixture 中途失敗：{exc}")
				self.report["counts_after"] = self._read_counts()
				self._set_status("fail")
				return self.report
			self.report["counts_after"] = self._read_counts()
			self._set_status_from_snapshot(existing=True)
			return self.report

		try:
			self.report["resume_mode"] = "new_fixture"
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
			"resume_state": {},
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
		self._record_stock_entry_difference_account(vehicle)
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

	def _resume_existing_fixture_flow(self, existing):
		self._apply_existing_fixture(existing)
		vehicle_name = existing.get("vehicle")
		self._set_resume_stage("vehicle_found")
		if not vehicle_name or not frappe.db.exists("Used Car Vehicle", vehicle_name):
			self._block("existing fixture 指向的 Used Car Vehicle 不存在。")
			return
		if self._submitted_sales_invoice_count() > 0:
			self._block("submitted Sales Invoice count 已大於 0，不可續跑 formal submit fixture。")
			return

		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		self._record_vehicle_state(vehicle)
		if not self._validate_no_existing_non_draft_sales_invoice(vehicle):
			return

		if not vehicle.get("stock_entry") or not vehicle.get("serial_no"):
			intake = VehicleIntakeService().complete_intake(vehicle.name)
			self._record_from_result(intake)
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle.name)
			self._record_vehicle_state(vehicle)
		self._set_resume_stage("intake_completed")

		if vehicle.get("status") in ("庫存中", "整備中"):
			VehicleListingService().list_vehicle(vehicle.name)
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle.name)
			self._record_vehicle_state(vehicle)
		self._set_resume_stage("listed")

		reservation = self._resolve_resume_reservation(vehicle)
		reservation_service = VehicleReservationService()
		if reservation and reservation.get("status") not in ("有效", "已完成"):
			self._block(f"existing fixture reservation 狀態不是有效 / 已完成：{reservation.get('status')}")
			return
		if not reservation:
			reservation_result = reservation_service.create_reservation(
				vehicle_name=vehicle.name,
				customer_name="P1 ACC 6F C QA Customer",
				customer_phone="0900000000",
				deposit_amount=10000,
				payment_method="現金",
				payment_reference=FIXTURE_MARKER,
				notes=FIXTURE_MARKER,
			)
			self._record_reservation_result(reservation_result, prefix="deposit")
			reservation = frappe.get_doc("Used Car Reservation", reservation_result.get("reservation"))
		else:
			self.report["reservation"] = reservation.name
			self.report["customer"] = reservation.get("customer")
		self._set_resume_stage("reservation_ready")

		if not self._ensure_resume_accounting_flow(reservation, "deposit"):
			return
		self._set_resume_stage("deposit_accounting_ready")

		reservation = frappe.get_doc("Used Car Reservation", reservation.name)
		if not self._resolve_resume_flow(reservation, "final").get("money_flow"):
			if reservation.get("status") != "有效":
				self._block("缺少尾款金流，但 reservation 不是有效狀態，不可補建尾款。")
				return
			final_result = reservation_service.create_final_payment_for_active_reservation(
				vehicle_name=vehicle.name,
				amount=990000,
				payment_method="現金",
				payment_reference=FIXTURE_MARKER,
				notes=FIXTURE_MARKER,
			)
			self._record_reservation_result(final_result, prefix="final")
			reservation = frappe.get_doc("Used Car Reservation", reservation.name)
		self._set_resume_stage("final_payment_ready")

		if not self._ensure_resume_accounting_flow(reservation, "final"):
			return
		self._set_resume_stage("final_accounting_ready")

		vehicle = frappe.get_doc("Used Car Vehicle", vehicle.name)
		if vehicle.get("status") != "已售出":
			preflight = reservation_service.preflight_delivery_for_active_reservation(vehicle.name)
			self._record_reservation_result(preflight, prefix="both")
			reservation_service.complete_active_reservation(vehicle.name, completion_note=FIXTURE_MARKER)
		elif not self._validate_sold_vehicle_completion_links(vehicle):
			return
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle.name)
		self._record_vehicle_state(vehicle)
		self._set_resume_stage("reservation_completed")

		readiness = FormalSalesInvoiceDraftReadinessService().run(vehicle.name)
		self.report["readiness_report"] = readiness
		self.report["readiness_status"] = readiness.get("status")
		if readiness.get("status") != "pass" or readiness.get("ready_to_create_sales_invoice_draft") is not True:
			self._block("readiness 未通過，不建立 Sales Invoice draft。")
			return
		self._set_resume_stage("readiness_pass")

		draft = GuardedFormalSalesInvoiceDraftCreationQAService().run(vehicle_name=vehicle.name, note=FIXTURE_MARKER)
		self.report["draft_creation_report"] = draft
		self.report["draft_creation_status"] = draft.get("status")
		self.report["sales_invoice"] = draft.get("sales_invoice")
		self.report["sales_invoice_docstatus"] = draft.get("sales_invoice_docstatus")
		if not draft.get("created") or not draft.get("sales_invoice"):
			self._block("guarded draft creation 未建立 Sales Invoice draft。")
			return
		if not self._validate_existing_sales_invoice(draft.get("sales_invoice")):
			return
		self._mark_sales_invoice(draft.get("sales_invoice"))
		self._set_resume_stage("draft_created")
		self._run_snapshot(draft.get("sales_invoice"))
		self._set_resume_stage("snapshot_pass")

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

	def _record_vehicle_state(self, vehicle):
		self._record_vehicle(vehicle)
		for key in ("item", "serial_no", "stock_entry"):
			self.report[key] = vehicle.get(key)
		self.report["resume_state"].update(
			{
				"vehicle": vehicle.name,
				"stock_no": vehicle.get("stock_no"),
				"item": vehicle.get("item"),
				"serial_no": vehicle.get("serial_no"),
				"stock_entry": vehicle.get("stock_entry"),
				"vehicle_status": vehicle.get("status"),
				"sales_invoice": vehicle.get("sales_invoice"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
			}
		)
		self._record_stock_entry_difference_account(vehicle)

	def _set_resume_stage(self, stage):
		self.report["resume_stage"] = stage
		self.report["validations"].append(f"resume_stage: {stage}")

	def _record_from_result(self, result):
		for key in ("item", "serial_no", "stock_entry", "stock_no"):
			if result.get(key):
				self.report[key] = result.get(key)

	def _record_stock_entry_difference_account(self, vehicle):
		service = VehicleStockService()
		company = service._resolve_company_for_stock_entry(vehicle)
		if frappe.db.exists("Company", company) and frappe.get_meta("Company").has_field("stock_adjustment_account"):
			self.report["stock_adjustment_account"] = frappe.db.get_value("Company", company, "stock_adjustment_account")
		if service._stock_entry_detail_has_expense_account():
			self.report["stock_entry_difference_account"] = service._resolve_stock_entry_difference_account(vehicle)

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

	def _resolve_resume_reservation(self, vehicle):
		for reservation_name in (
			vehicle.get("completed_reservation"),
			frappe.db.get_value("Used Car Reservation", {"vehicle": vehicle.name, "status": "有效"}, "name", order_by="modified desc"),
			frappe.db.get_value("Used Car Reservation", {"vehicle": vehicle.name, "status": "已完成"}, "name", order_by="modified desc"),
			frappe.db.get_value("Used Car Reservation", {"vehicle": vehicle.name, "notes": ["like", f"%{FIXTURE_MARKER}%"]}, "name", order_by="modified desc"),
		):
			if reservation_name and frappe.db.exists("Used Car Reservation", reservation_name):
				return frappe.get_doc("Used Car Reservation", reservation_name)
		return None

	def _ensure_resume_accounting_flow(self, reservation, prefix):
		flow = self._resolve_resume_flow(reservation, prefix)
		label = "訂金" if prefix == "deposit" else "尾款"
		self._record_resume_flow(flow, prefix)
		if flow.get("money_flow") and not flow.get("voucher_draft"):
			self._block(f"{label}已有 money_flow 但沒有 voucher_draft，不可硬修。")
			return False
		if not flow.get("money_flow") or not flow.get("voucher_draft"):
			if prefix == "deposit" and reservation.get("status") == "有效":
				self._block("缺少訂金金流或傳票草稿，請先確認既有保留流程狀態；resume 不直接建立孤立訂金資料。")
			else:
				self._block(f"缺少{label}金流或傳票草稿。")
			return False
		if flow.get("voucher_journal_entry") and flow.get("money_flow_journal_entry") and flow.get("voucher_journal_entry") != flow.get("money_flow_journal_entry"):
			self._block(f"{label}傳票草稿 linked 到 unexpected Journal Entry。")
			return False
		if flow.get("voucher_status") == "待審核":
			confirm = VehicleVoucherService().confirm_voucher_draft(flow.get("voucher_draft"), FIXTURE_MARKER)
			self.report[f"{prefix}_journal_entry"] = confirm.get("journal_entry")
			return True
		if flow.get("voucher_status") == "已入帳" and flow.get("voucher_journal_entry"):
			self.report[f"{prefix}_journal_entry"] = flow.get("voucher_journal_entry")
			return True
		self._block(f"{label}傳票草稿狀態不是待審核 / 已入帳，或缺少 Journal Entry。")
		return False

	def _resolve_resume_flow(self, reservation, prefix):
		flow_type = "訂金收款" if prefix == "deposit" else "尾款收款"
		money_field = "money_flow" if prefix == "deposit" else "final_money_flow"
		voucher_field = "voucher_draft" if prefix == "deposit" else "final_voucher_draft"
		money_flow = reservation.get(money_field) or frappe.db.get_value(
			"Used Car Money Flow",
			{"reservation": reservation.name, "flow_type": flow_type, "status": ["!=", "已作廢"]},
			"name",
			order_by="modified desc",
		)
		voucher_draft = reservation.get(voucher_field)
		if money_flow and (not voucher_draft or not frappe.db.exists("Used Car Voucher Draft", voucher_draft)):
			voucher_draft = frappe.db.get_value(
				"Used Car Voucher Draft",
				{"money_flow": money_flow, "status": ["!=", "已作廢"]},
				"name",
				order_by="modified desc",
			)
		money_doc = frappe.get_doc("Used Car Money Flow", money_flow) if money_flow and frappe.db.exists("Used Car Money Flow", money_flow) else None
		voucher_doc = frappe.get_doc("Used Car Voucher Draft", voucher_draft) if voucher_draft and frappe.db.exists("Used Car Voucher Draft", voucher_draft) else None
		return {
			"money_flow": money_flow,
			"voucher_draft": voucher_draft,
			"money_flow_status": money_doc.get("status") if money_doc else None,
			"voucher_status": voucher_doc.get("status") if voucher_doc else None,
			"money_flow_journal_entry": money_doc.get("journal_entry") if money_doc else None,
			"voucher_journal_entry": voucher_doc.get("journal_entry") if voucher_doc else None,
		}

	def _record_resume_flow(self, flow, prefix):
		self.report[f"{prefix}_money_flow"] = flow.get("money_flow")
		self.report[f"{prefix}_voucher_draft"] = flow.get("voucher_draft")
		self.report[f"{prefix}_journal_entry"] = flow.get("voucher_journal_entry") or flow.get("money_flow_journal_entry")
		self.report["resume_state"][f"{prefix}_money_flow_status"] = flow.get("money_flow_status")
		self.report["resume_state"][f"{prefix}_voucher_status"] = flow.get("voucher_status")

	def _validate_existing_sales_invoice(self, sales_invoice):
		if not sales_invoice or not frappe.db.exists("Sales Invoice", sales_invoice):
			self._block("existing fixture Sales Invoice 不存在。")
			return False
		docstatus = int(getattr(frappe.get_doc("Sales Invoice", sales_invoice), "docstatus", 0) or 0)
		self.report["sales_invoice_docstatus"] = docstatus
		if docstatus != 0:
			self._block("existing fixture 指向的 Sales Invoice 不是 Draft，不可續跑。")
			return False
		return True

	def _validate_no_existing_non_draft_sales_invoice(self, vehicle):
		sales_invoice = vehicle.get("sales_invoice")
		if not sales_invoice:
			return True
		self.report["sales_invoice"] = sales_invoice
		if not frappe.db.exists("Sales Invoice", sales_invoice):
			self._block("vehicle.sales_invoice 指向不存在的 Sales Invoice。")
			return False
		return self._validate_existing_sales_invoice(sales_invoice)

	def _validate_sold_vehicle_completion_links(self, vehicle):
		missing = [
			fieldname
			for fieldname in (
				"completed_reservation",
				"deposit_money_flow",
				"deposit_voucher_draft",
				"deposit_journal_entry",
				"final_money_flow",
				"final_voucher_draft",
				"final_journal_entry",
			)
			if not vehicle.get(fieldname)
		]
		if missing:
			self._block(f"vehicle 已售出但缺少 completion summary links：{', '.join(missing)}")
			return False
		return True

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
		if existing.get("vehicle") and not existing.get("sales_invoice"):
			self.report["validations"].append("已找到半套 formal submit fixture，將透過既有正式 service 安全續跑。")
		if existing.get("vehicle") and frappe.db.exists("Used Car Vehicle", existing.get("vehicle")):
			self._record_stock_entry_difference_account(frappe.get_doc("Used Car Vehicle", existing.get("vehicle")))

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


def inspect_formal_submit_fixture_resume_state_payload():
	existing = find_existing_formal_submit_fixture()
	vehicle_name = existing.get("vehicle")
	state = {
		"site": getattr(getattr(frappe, "local", None), "site", None),
		"fixture_marker": FIXTURE_MARKER,
		"existing_fixture": existing,
		"submitted_sales_invoice_count": frappe.db.count("Sales Invoice", {"docstatus": 1}),
		"resume_mode": "existing_draft" if existing.get("sales_invoice") else "half_fixture_resume" if vehicle_name else "new_fixture",
		"resume_stage": "snapshot_pass" if existing.get("sales_invoice") else "vehicle_found" if vehicle_name else None,
		"resume_state": {},
	}
	if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		state["resume_state"].update(
			{
				"vehicle": vehicle.name,
				"stock_no": vehicle.get("stock_no"),
				"item": vehicle.get("item"),
				"serial_no": vehicle.get("serial_no"),
				"stock_entry": vehicle.get("stock_entry"),
				"vehicle_status": vehicle.get("status"),
				"completed_reservation": vehicle.get("completed_reservation"),
				"sales_invoice": vehicle.get("sales_invoice"),
				"formal_delivery_status": vehicle.get("formal_delivery_status"),
				"stock_entry_difference_account": _inspect_stock_entry_difference_account(vehicle),
			}
		)
		reservation_name = vehicle.get("completed_reservation") or frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle.name, "status": ["in", ["有效", "已完成"]]},
			"name",
			order_by="modified desc",
		)
		if reservation_name and frappe.db.exists("Used Car Reservation", reservation_name):
			reservation = frappe.get_doc("Used Car Reservation", reservation_name)
			state["resume_state"].update(_inspect_reservation_state(reservation))
	return state


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


def _inspect_stock_entry_difference_account(vehicle):
	try:
		service = VehicleStockService()
		if service._stock_entry_detail_has_expense_account():
			return service._resolve_stock_entry_difference_account(vehicle)
	except Exception as exc:
		return f"blocked: {exc}"
	return None


def _inspect_reservation_state(reservation):
	state = {
		"reservation": reservation.name,
		"reservation_status": reservation.get("status"),
		"customer": reservation.get("customer"),
	}
	for prefix, flow_type, money_field, voucher_field in (
		("deposit", "訂金收款", "money_flow", "voucher_draft"),
		("final", "尾款收款", "final_money_flow", "final_voucher_draft"),
	):
		money_flow = reservation.get(money_field) or frappe.db.get_value(
			"Used Car Money Flow",
			{"reservation": reservation.name, "flow_type": flow_type, "status": ["!=", "已作廢"]},
			"name",
			order_by="modified desc",
		)
		voucher_draft = reservation.get(voucher_field)
		if money_flow and (not voucher_draft or not frappe.db.exists("Used Car Voucher Draft", voucher_draft)):
			voucher_draft = frappe.db.get_value(
				"Used Car Voucher Draft",
				{"money_flow": money_flow, "status": ["!=", "已作廢"]},
				"name",
				order_by="modified desc",
			)
		money_doc = frappe.get_doc("Used Car Money Flow", money_flow) if money_flow and frappe.db.exists("Used Car Money Flow", money_flow) else None
		voucher_doc = frappe.get_doc("Used Car Voucher Draft", voucher_draft) if voucher_draft and frappe.db.exists("Used Car Voucher Draft", voucher_draft) else None
		state[f"{prefix}_money_flow"] = money_flow
		state[f"{prefix}_money_flow_status"] = money_doc.get("status") if money_doc else None
		state[f"{prefix}_voucher_draft"] = voucher_draft
		state[f"{prefix}_voucher_status"] = voucher_doc.get("status") if voucher_doc else None
		state[f"{prefix}_journal_entry"] = (voucher_doc.get("journal_entry") if voucher_doc else None) or (money_doc.get("journal_entry") if money_doc else None)
	return state


@frappe.whitelist()
def run_formal_submitted_sales_invoice_test_fixture_setup():
	return FormalSubmittedSalesInvoiceTestFixtureSetupService().run()


@frappe.whitelist()
def inspect_formal_submit_fixture_resume_state():
	return inspect_formal_submit_fixture_resume_state_payload()
