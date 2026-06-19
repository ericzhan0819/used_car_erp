import frappe
from frappe.utils import flt, nowdate

from used_car_erp.used_car_erp.services.advance_settlement_readiness_service import AdvanceSettlementReadinessService
from used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service import COMPANY
from used_car_erp.used_car_erp.services.used_car_controlled_write_service import db_set_service_controlled_values


EXPECTED_SITE = "erpnext-coa.test"
CONFIRMATION_TOKEN = "P1-ACC-6G-1-SETTLE"
ACTION = "used_car_formal_delivery.advance_settlement.link"
ROUNDING_TOLERANCE = 0.01

COUNT_DOCTYPES = (
	"Journal Entry",
	"GL Entry",
	"Sales Invoice",
	"Sales Invoice docstatus=1",
	"Payment Entry",
	"Delivery Note",
	"Stock Entry",
	"Purchase Invoice",
)

REPORT_KEYS = (
	"status",
	"created",
	"submitted",
	"already_settled",
	"ready_for_review",
	"site",
	"sales_invoice",
	"vehicle",
	"reservation",
	"customer",
	"company",
	"advance_total",
	"receivable_account",
	"settlement_preview",
	"journal_entry",
	"journal_entry_docstatus",
	"sales_invoice_outstanding_before",
	"sales_invoice_outstanding_after",
	"counts_before",
	"counts_after",
	"count_deltas",
	"gl_entry_count_for_journal_entry",
	"gl_accounts_for_journal_entry",
	"readiness_status",
	"readiness_report",
	"planned_vehicle_updates",
	"applied_vehicle_updates",
	"validations",
	"warnings",
	"blocking_errors",
)


class GuardedAdvanceSettlementJournalQAService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, sales_invoice=None, vehicle_name=None, confirmation_token=None):
		self.report["site"] = self._site()
		if self.report["site"] != EXPECTED_SITE:
			self._block(f"advance settlement QA 只能在 {EXPECTED_SITE} 執行，目前站台是 {self.report['site']}。")
			self._set_status("blocked")
			return self.report

		if confirmation_token != CONFIRMATION_TOKEN:
			self._block("confirmation token 不正確，不建立或提交 Journal Entry。")
			self._set_status("blocked")
			return self.report

		if self._observe_existing_submitted_settlement(sales_invoice=sales_invoice, vehicle_name=vehicle_name):
			self._set_status("already_settled")
			return self.report

		readiness = AdvanceSettlementReadinessService().run(sales_invoice=sales_invoice, vehicle_name=vehicle_name)
		self._read_readiness(readiness)
		if self.report["blocking_errors"]:
			vehicle = self._get_vehicle(self.report["vehicle"])
			if self._observe_already_settled(vehicle):
				self.report["blocking_errors"] = []
				self._set_status("already_settled")
				return self.report
		if self.report["blocking_errors"]:
			self._set_status("blocked")
			return self.report

		vehicle = self._get_vehicle(self.report["vehicle"])
		invoice = self._get_invoice(self.report["sales_invoice"])
		self._read_invoice_outstanding(invoice, before=True)
		self._validate_target(vehicle, invoice)
		if self._observe_already_settled(vehicle):
			self._set_status("already_settled")
			return self.report
		if self.report["blocking_errors"]:
			self._set_status("blocked")
			return self.report

		accounts = self._build_accounts_from_preview()
		self.report["counts_before"] = self._read_counts()
		if self.report["blocking_errors"]:
			self._set_status("blocked")
			return self.report

		try:
			journal_entry = self._create_journal_entry(invoice, accounts)
			self.report["created"] = True
			self.report["journal_entry"] = journal_entry.name
			journal_entry.submit()
			self.report["submitted"] = True
			self.report["journal_entry_docstatus"] = int(journal_entry.get("docstatus") or getattr(journal_entry, "docstatus", 0) or 0)
			frappe.db.commit()
		except Exception as exc:
			self._block(f"advance settlement Journal Entry insert / submit 失敗：{exc}")
			self.report["counts_after"] = self._read_counts()
			self._record_count_deltas()
			self._set_status("fail")
			return self.report

		try:
			self._link_vehicle(vehicle.name, journal_entry.name)
			frappe.db.commit()
		except Exception as exc:
			self._block(f"advance settlement vehicle link 寫入失敗：{exc}")

		self._read_after_submit(journal_entry.name)
		self._validate_after_submit()
		self._set_status("warning" if self.report["blocking_errors"] else "pass")
		return self.report

	def _new_report(self):
		list_keys = {"settlement_preview", "gl_accounts_for_journal_entry", "validations", "warnings", "blocking_errors"}
		return {key: [] if key in list_keys else None for key in REPORT_KEYS} | {
			"status": "fail",
			"created": False,
			"submitted": False,
			"already_settled": False,
			"ready_for_review": False,
			"advance_total": 0,
			"counts_before": None,
			"counts_after": None,
			"count_deltas": None,
			"gl_entry_count_for_journal_entry": 0,
			"planned_vehicle_updates": {},
			"applied_vehicle_updates": {},
		}

	def _site(self):
		return getattr(getattr(frappe, "local", None), "site", None)

	def _observe_existing_submitted_settlement(self, sales_invoice=None, vehicle_name=None):
		vehicle = None
		if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		elif sales_invoice:
			vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": sales_invoice}, "name")
			if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
				vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		if not vehicle:
			return False
		self.report["vehicle"] = vehicle.name
		self.report["sales_invoice"] = vehicle.get("sales_invoice") or sales_invoice
		linked_journal = vehicle.get("advance_settlement_journal_entry")
		if not linked_journal:
			return False
		docstatus = frappe.db.get_value("Journal Entry", linked_journal, "docstatus")
		if int(docstatus or 0) != 1:
			return False
		self.report["already_settled"] = True
		self.report["journal_entry"] = linked_journal
		self.report["journal_entry_docstatus"] = 1
		self.report["counts_before"] = self._read_counts()
		self.report["counts_after"] = dict(self.report["counts_before"])
		self._record_count_deltas()
		self._read_journal_gl(linked_journal)
		return True

	def _read_readiness(self, readiness):
		self.report["readiness_report"] = readiness
		self.report["readiness_status"] = readiness.get("status")
		for key in ("company", "sales_invoice", "vehicle", "reservation", "customer", "receivable_account", "advance_total"):
			self.report[key] = readiness.get(key)
		self.report["settlement_preview"] = list(readiness.get("settlement_preview") or [])
		if readiness.get("status") != "pass" or readiness.get("ready_to_create_advance_settlement") is not True:
			self._block("advance settlement readiness 未通過，不建立 Journal Entry。")
		if not self.report["settlement_preview"]:
			self._block("advance settlement readiness 缺少 settlement_preview。")

	def _get_vehicle(self, vehicle_name):
		if not vehicle_name or not frappe.db.exists("Used Car Vehicle", vehicle_name):
			self._block(f"Used Car Vehicle 不存在：{vehicle_name}")
			return None
		return frappe.get_doc("Used Car Vehicle", vehicle_name)

	def _get_invoice(self, invoice_name):
		if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
			self._block(f"Sales Invoice 不存在：{invoice_name}")
			return None
		return frappe.get_doc("Sales Invoice", invoice_name)

	def _read_invoice_outstanding(self, invoice, before=False):
		if not invoice:
			return
		key = "sales_invoice_outstanding_before" if before else "sales_invoice_outstanding_after"
		self.report[key] = flt(getattr(invoice, "outstanding_amount", 0))

	def _validate_target(self, vehicle, invoice):
		if not vehicle or not invoice:
			return
		if vehicle.get("sales_invoice") != self.report["sales_invoice"]:
			self._block("Used Car Vehicle.sales_invoice 必須等於 target Sales Invoice。")
		if vehicle.get("formal_delivery_status") != "已完成":
			self._block("Used Car Vehicle formal_delivery_status 必須是 已完成。")
		linked_journal = vehicle.get("advance_settlement_journal_entry")
		if linked_journal:
			if frappe.db.exists("Journal Entry", linked_journal) and int(frappe.db.get_value("Journal Entry", linked_journal, "docstatus") or 0) == 1:
				return
			self._block("Used Car Vehicle 已有 advance_settlement_journal_entry，但不存在或未提交。")
		if int(getattr(invoice, "docstatus", 0) or 0) != 1:
			self._block("Sales Invoice docstatus 必須是 1。")
		if getattr(invoice, "company", None) != COMPANY:
			self._block(f"Sales Invoice company 必須是 {COMPANY}。")

	def _observe_already_settled(self, vehicle):
		if not vehicle or self.report["blocking_errors"]:
			return False
		linked_journal = vehicle.get("advance_settlement_journal_entry")
		if not linked_journal:
			return False
		docstatus = frappe.db.get_value("Journal Entry", linked_journal, "docstatus")
		if int(docstatus or 0) != 1:
			return False
		self.report["already_settled"] = True
		self.report["journal_entry"] = linked_journal
		self.report["journal_entry_docstatus"] = 1
		self.report["counts_before"] = self._read_counts()
		self.report["counts_after"] = dict(self.report["counts_before"])
		self._record_count_deltas()
		self._read_journal_gl(linked_journal)
		return True

	def _read_counts(self):
		counts = {}
		for doctype in COUNT_DOCTYPES:
			if doctype == "Sales Invoice docstatus=1":
				counts[doctype] = frappe.db.count("Sales Invoice", {"docstatus": 1})
			else:
				counts[doctype] = frappe.db.count(doctype)
		return counts

	def _build_accounts_from_preview(self):
		accounts = []
		debit_total = 0
		credit_total = 0
		for row in self.report["settlement_preview"]:
			debit = flt(row.get("debit"))
			credit = flt(row.get("credit"))
			debit_total += debit
			credit_total += credit
			account_row = {
				"account": row.get("account"),
				"debit_in_account_currency": debit,
				"credit_in_account_currency": credit,
			}
			if credit > 0:
				account_row["reference_type"] = "Sales Invoice"
				account_row["reference_name"] = self.report["sales_invoice"]
				account_row["party_type"] = "Customer"
				account_row["party"] = self.report["customer"]
			accounts.append(account_row)
		self.report["validations"].append({"journal_debit_total": debit_total, "journal_credit_total": credit_total})
		if flt(debit_total, 2) != flt(credit_total, 2):
			self._block("settlement preview debit / credit 不平，不建立 Journal Entry。")
		if flt(debit_total, 2) != flt(self.report["advance_total"], 2):
			self._block("settlement preview debit total 必須等於 advance_total。")
		return accounts

	def _create_journal_entry(self, invoice, accounts):
		posting_date = getattr(invoice, "posting_date", None) or nowdate()
		values = {
			"doctype": "Journal Entry",
			"company": self.report["company"],
			"posting_date": posting_date,
			"accounts": accounts,
		}
		meta = frappe.get_meta("Journal Entry")
		if meta.has_field("voucher_type"):
			values["voucher_type"] = "Journal Entry"
		if meta.has_field("entry_type"):
			values["entry_type"] = "Journal Entry"
		remark = self._remark()
		if meta.has_field("user_remark"):
			values["user_remark"] = remark
		if meta.has_field("remark"):
			values["remark"] = remark
		return frappe.get_doc(values).insert()

	def _remark(self):
		return "\n".join(
			str(part)
			for part in (
				"P1-ACC-6G-1 Advance Settlement",
				f"Sales Invoice: {self.report['sales_invoice']}",
				f"Vehicle: {self.report['vehicle']}",
				f"Reservation: {self.report['reservation']}",
			)
			if part
		)

	def _link_vehicle(self, vehicle_name, journal_entry_name):
		updates = {"advance_settlement_journal_entry": journal_entry_name}
		self.report["planned_vehicle_updates"] = dict(updates)
		db_set_service_controlled_values("Used Car Vehicle", vehicle_name, action=ACTION, values=updates)
		self.report["applied_vehicle_updates"] = dict(updates)

	def _read_after_submit(self, journal_entry_name):
		self.report["counts_after"] = self._read_counts()
		self._record_count_deltas()
		if frappe.db.exists("Journal Entry", journal_entry_name):
			journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
			self.report["journal_entry_docstatus"] = int(journal_entry.get("docstatus") or 0)
		invoice = self._get_invoice(self.report["sales_invoice"])
		self._read_invoice_outstanding(invoice, before=False)
		self._read_journal_gl(journal_entry_name)

	def _record_count_deltas(self):
		before = self.report.get("counts_before") or {}
		after = self.report.get("counts_after") or {}
		self.report["count_deltas"] = {doctype: after.get(doctype, 0) - before.get(doctype, 0) for doctype in COUNT_DOCTYPES}

	def _read_journal_gl(self, journal_entry_name):
		entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_type": "Journal Entry", "voucher_no": journal_entry_name},
			fields=("account", "debit", "credit"),
			order_by="account asc",
		)
		self.report["gl_entry_count_for_journal_entry"] = len(entries)
		self.report["gl_accounts_for_journal_entry"] = [
			{"account": row.get("account"), "debit": flt(row.get("debit")), "credit": flt(row.get("credit"))} for row in entries
		]

	def _validate_after_submit(self):
		if not self.report.get("journal_entry") or not frappe.db.exists("Journal Entry", self.report["journal_entry"]):
			self._block("submit 後 Journal Entry 不存在。")
		if self.report.get("journal_entry_docstatus") != 1:
			self._block("submit 後 Journal Entry docstatus 必須是 1。")
		vehicle = self._get_vehicle(self.report["vehicle"])
		if vehicle and vehicle.get("advance_settlement_journal_entry") != self.report["journal_entry"]:
			self._block("Vehicle.advance_settlement_journal_entry 未正確回寫。")
		if self.report["gl_entry_count_for_journal_entry"] <= 0:
			self._block("找不到 Journal Entry 對應 GL Entry。")
		if abs(flt(self.report.get("sales_invoice_outstanding_after"))) > ROUNDING_TOLERANCE:
			self._block("Sales Invoice outstanding_amount 未歸零；不自動修正。")
		self._validate_count_deltas()

	def _validate_count_deltas(self):
		deltas = self.report.get("count_deltas") or {}
		if deltas.get("Journal Entry") != 1:
			self._block("Journal Entry count submit 前後必須增加 1。")
		if deltas.get("GL Entry", 0) <= 0:
			self._block("GL Entry count submit 後必須增加。")
		for doctype in ("Sales Invoice", "Sales Invoice docstatus=1", "Payment Entry", "Delivery Note", "Stock Entry", "Purchase Invoice"):
			if deltas.get(doctype) != 0:
				self._block(f"{doctype} count submit 前後不可改變。")

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _set_status(self, status):
		self.report["status"] = status
		self.report["ready_for_review"] = (self.report["submitted"] or self.report["already_settled"]) and not self.report["blocking_errors"]


@frappe.whitelist()
def run_guarded_advance_settlement_journal_qa(sales_invoice=None, vehicle_name=None, confirmation_token=None):
	return GuardedAdvanceSettlementJournalQAService().run(
		sales_invoice=sales_invoice,
		vehicle_name=vehicle_name,
		confirmation_token=confirmation_token,
	)
