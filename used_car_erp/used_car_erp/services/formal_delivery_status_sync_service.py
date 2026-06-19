import frappe
from frappe.utils import now

from used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service import COMPANY
from used_car_erp.used_car_erp.services.used_car_controlled_write_service import db_set_service_controlled_values


EXPECTED_SITE = "erpnext-coa.test"
ACTION = "used_car_formal_delivery.status.sync"
SYNC_NOTE_TEMPLATE = "Sales Invoice submitted and native ERPNext GL/SLE confirmed: {sales_invoice}"

REPORT_KEYS = (
	"status",
	"dry_run",
	"synced",
	"already_synced",
	"site",
	"sales_invoice",
	"sales_invoice_docstatus",
	"sales_invoice_posting_date",
	"company",
	"customer",
	"vehicle",
	"vehicle_status",
	"formal_delivery_status_before",
	"formal_delivery_status_after",
	"formal_delivery_posting_date_before",
	"formal_delivery_posting_date_after",
	"gl_entry_count",
	"stock_ledger_entry_count",
	"payment_entry_count",
	"delivery_note_count",
	"purchase_invoice_count",
	"journal_entry_count",
	"stock_entry_count",
	"planned_updates",
	"applied_updates",
	"validations",
	"warnings",
	"blocking_errors",
)

SIDE_EFFECT_DOCTYPES = (
	"Payment Entry",
	"Delivery Note",
	"Purchase Invoice",
	"Journal Entry",
	"Stock Entry",
)

SIDE_EFFECT_LINK_FIELDS = {
	"Payment Entry": "reference_name",
	"Delivery Note": "against_sales_invoice",
	"Purchase Invoice": "bill_no",
	"Journal Entry": "cheque_no",
	"Stock Entry": "sales_invoice_no",
}


class FormalDeliveryStatusSyncService:
	def __init__(self):
		self.report = self._new_report()

	def inspect(self, sales_invoice=None):
		return self.run(sales_invoice=sales_invoice, dry_run=1)

	def run(self, sales_invoice=None, dry_run=1):
		self.report["dry_run"] = self._as_bool(dry_run)
		self.report["site"] = self._site()
		target = sales_invoice or self._find_default_target()
		self.report["sales_invoice"] = target

		if not self.report["dry_run"] and self.report["site"] != EXPECTED_SITE:
			self._block(f"formal delivery status sync 只能在 {EXPECTED_SITE} 寫入，目前站台是 {self.report['site']}。")
			self._set_status()
			return self.report

		if not target or not frappe.db.exists("Sales Invoice", target):
			self._block(f"Sales Invoice 不存在：{target}")
			self._set_status()
			return self.report

		invoice = frappe.get_doc("Sales Invoice", target)
		vehicle = self._resolve_linked_vehicle(target)
		self._read_invoice(invoice)
		self._read_vehicle(vehicle)
		self._read_target_counts(target)
		self._validate(invoice, vehicle)
		self._plan_updates(invoice, vehicle)

		if self.report["blocking_errors"] or self.report["dry_run"] or self.report["already_synced"]:
			self._set_status()
			return self.report

		try:
			updates = dict(self.report["planned_updates"])
			db_set_service_controlled_values(
				"Used Car Vehicle",
				vehicle.name,
				action=ACTION,
				values=updates,
			)
			frappe.db.commit()
		except Exception as exc:
			self._block(f"formal delivery status sync 寫入失敗：{exc}")
			self.report["status"] = "fail"
			return self.report

		self.report["synced"] = True
		self.report["applied_updates"] = dict(self.report["planned_updates"])
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle.name)
		self._read_vehicle_after(vehicle)
		self._set_status()
		return self.report

	def _new_report(self):
		list_keys = {"validations", "warnings", "blocking_errors"}
		return {key: [] if key in list_keys else None for key in REPORT_KEYS} | {
			"status": "fail",
			"dry_run": True,
			"synced": False,
			"already_synced": False,
			"gl_entry_count": 0,
			"stock_ledger_entry_count": 0,
			"payment_entry_count": 0,
			"delivery_note_count": 0,
			"purchase_invoice_count": 0,
			"journal_entry_count": 0,
			"stock_entry_count": 0,
			"planned_updates": {},
			"applied_updates": {},
		}

	def _as_bool(self, value):
		return str(value).lower() not in {"0", "false", "no"}

	def _site(self):
		return getattr(getattr(frappe, "local", None), "site", None)

	def _find_default_target(self):
		vehicles = frappe.db.get_all(
			"Used Car Vehicle",
			filters={"sales_invoice": ["is", "set"], "status": "已售出", "formal_delivery_status": ["in", ["銷售發票草稿", "已完成"]]},
			fields=("name", "sales_invoice"),
			order_by="modified desc",
			limit=50,
		)
		for vehicle in vehicles:
			invoice_name = vehicle.get("sales_invoice")
			if not invoice_name or not frappe.db.exists("Sales Invoice", invoice_name):
				continue
			invoice = frappe.get_doc("Sales Invoice", invoice_name)
			if getattr(invoice, "company", None) == COMPANY and int(getattr(invoice, "docstatus", 0) or 0) == 1:
				return invoice_name
		return None

	def _resolve_linked_vehicle(self, invoice_name):
		vehicle_name = frappe.db.get_value("Used Car Vehicle", {"sales_invoice": invoice_name}, "name")
		if not vehicle_name:
			return None
		return frappe.get_doc("Used Car Vehicle", vehicle_name)

	def _read_invoice(self, invoice):
		self.report.update(
			{
				"sales_invoice_docstatus": int(getattr(invoice, "docstatus", 0) or 0),
				"sales_invoice_posting_date": getattr(invoice, "posting_date", None),
				"company": getattr(invoice, "company", None),
				"customer": getattr(invoice, "customer", None),
			}
		)

	def _read_vehicle(self, vehicle):
		if not vehicle:
			return
		self.report.update(
			{
				"vehicle": getattr(vehicle, "name", None),
				"vehicle_status": vehicle.get("status"),
				"formal_delivery_status_before": vehicle.get("formal_delivery_status"),
				"formal_delivery_status_after": vehicle.get("formal_delivery_status"),
				"formal_delivery_posting_date_before": vehicle.get("formal_delivery_posting_date"),
				"formal_delivery_posting_date_after": vehicle.get("formal_delivery_posting_date"),
			}
		)

	def _read_vehicle_after(self, vehicle):
		self.report["formal_delivery_status_after"] = vehicle.get("formal_delivery_status")
		self.report["formal_delivery_posting_date_after"] = vehicle.get("formal_delivery_posting_date")

	def _read_target_counts(self, target):
		self.report["gl_entry_count"] = frappe.db.count("GL Entry", {"voucher_type": "Sales Invoice", "voucher_no": target})
		self.report["stock_ledger_entry_count"] = frappe.db.count(
			"Stock Ledger Entry", {"voucher_type": "Sales Invoice", "voucher_no": target}
		)
		for doctype in SIDE_EFFECT_DOCTYPES:
			key = doctype.lower().replace(" ", "_") + "_count"
			self.report[key] = self._count_optional_target_link(doctype, target)

	def _count_optional_target_link(self, doctype, target):
		fieldname = SIDE_EFFECT_LINK_FIELDS.get(doctype)
		if not fieldname or not frappe.get_meta(doctype).has_field(fieldname):
			return 0
		return frappe.db.count(doctype, {fieldname: target})

	def _validate(self, invoice, vehicle):
		if int(getattr(invoice, "docstatus", 0) or 0) != 1:
			self._block("target Sales Invoice docstatus 必須是 1。")
		if getattr(invoice, "company", None) != COMPANY:
			self._block(f"target Sales Invoice company 必須是 {COMPANY}。")
		if not vehicle:
			self._block("target Sales Invoice 沒有 linked Used Car Vehicle。")
			return
		if vehicle.get("status") != "已售出":
			self._block("linked Used Car Vehicle status 必須是 已售出。")
		if vehicle.get("sales_invoice") != invoice.name:
			self._block("linked Used Car Vehicle.sales_invoice 必須等於 target。")
		formal_status = vehicle.get("formal_delivery_status")
		if formal_status == "已完成":
			self.report["already_synced"] = True
		elif formal_status != "銷售發票草稿":
			self._block("linked Used Car Vehicle formal_delivery_status 必須是 銷售發票草稿 或 已完成。")
		if self.report["gl_entry_count"] <= 0:
			self._block("找不到 target Sales Invoice 對應 GL Entry。")
		if self.report["stock_ledger_entry_count"] <= 0:
			self._block("找不到 target Sales Invoice 對應 Stock Ledger Entry。")
		for key, label in (
			("payment_entry_count", "Payment Entry"),
			("delivery_note_count", "Delivery Note"),
			("purchase_invoice_count", "Purchase Invoice"),
			("journal_entry_count", "Journal Entry"),
			("stock_entry_count", "Stock Entry"),
		):
			if self.report[key] > 0:
				self._warn(f"target Sales Invoice 已查到對應 {label}；本 sync 不刪除也不修改。")

	def _plan_updates(self, invoice, vehicle):
		if self.report["blocking_errors"] or not vehicle or self.report["already_synced"]:
			return
		updates = {
			"formal_delivery_status": "已完成",
			"formal_delivery_completed_at": now(),
			"formal_delivery_completed_by": getattr(frappe.session, "user", None),
			"formal_delivery_note": SYNC_NOTE_TEMPLATE.format(sales_invoice=invoice.name),
		}
		meta = frappe.get_meta("Used Car Vehicle")
		if meta.has_field("formal_delivery_posting_date") and not vehicle.get("formal_delivery_posting_date"):
			updates["formal_delivery_posting_date"] = getattr(invoice, "posting_date", None)
		self.report["planned_updates"] = updates
		if self.report["dry_run"]:
			self.report["formal_delivery_status_after"] = updates["formal_delivery_status"]
			self.report["formal_delivery_posting_date_after"] = updates.get(
				"formal_delivery_posting_date", self.report["formal_delivery_posting_date_before"]
			)

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _warn(self, message):
		self.report["warnings"].append(message)

	def _set_status(self):
		if self.report["status"] == "fail" and self.report["blocking_errors"] and not self.report["synced"]:
			self.report["status"] = "blocked"
		elif self.report["already_synced"]:
			self.report["status"] = "already_synced"
		elif self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"


@frappe.whitelist()
def run_formal_delivery_status_sync(sales_invoice=None, dry_run=1):
	return FormalDeliveryStatusSyncService().run(sales_invoice=sales_invoice, dry_run=dry_run)


@frappe.whitelist()
def inspect_formal_delivery_status_sync(sales_invoice=None):
	return FormalDeliveryStatusSyncService().inspect(sales_invoice=sales_invoice)
