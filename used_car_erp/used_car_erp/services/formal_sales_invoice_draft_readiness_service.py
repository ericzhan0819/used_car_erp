import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.doctype.used_car_vehicle.used_car_vehicle import (
	derive_vehicle_tax_mode_from_purchase_document_type,
)
from used_car_erp.used_car_erp.services.vehicle_reservation_service import (
	SALES_TAX_ACCOUNT,
	SALES_TAX_RATE,
	SALES_TAX_TEMPLATE,
)


COMPANY = "OO"

REPORT_KEYS = (
	"status",
	"ready_to_create_sales_invoice_draft",
	"company",
	"vehicle",
	"vehicle_status",
	"formal_delivery_status",
	"sales_invoice",
	"reservation",
	"reservation_status",
	"customer",
	"item",
	"serial_no",
	"warehouse",
	"income_account",
	"sales_amount",
	"vehicle_tax_mode",
	"tax_review_status",
	"taxes_and_charges",
	"tax_account",
	"deposit_money_flow",
	"deposit_money_flow_status",
	"deposit_voucher_draft",
	"deposit_voucher_draft_status",
	"deposit_journal_entry",
	"final_money_flow",
	"final_money_flow_status",
	"final_voucher_draft",
	"final_voucher_draft_status",
	"final_journal_entry",
	"validations",
	"warnings",
	"blocking_errors",
)


class FormalSalesInvoiceDraftReadinessService:
	def __init__(self):
		self.report = self._new_report()

	def run(self, vehicle_name=None):
		vehicle_name = vehicle_name or self._find_latest_candidate_name()
		if not vehicle_name:
			self._block("找不到可檢查的正式 Sales Invoice 草稿建立候選車輛。")
			self._set_status()
			return self.report

		self.report["vehicle"] = vehicle_name
		if not frappe.db.exists("Used Car Vehicle", vehicle_name):
			self._block(f"Used Car Vehicle 不存在：{vehicle_name}")
			self._set_status()
			return self.report

		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		self._validate_vehicle(vehicle)
		reservation = self._resolve_completed_reservation(vehicle)
		if reservation:
			self._validate_reservation(reservation)
			self._validate_completion_links(vehicle, reservation)
			self._resolve_sales_amount(reservation)
		self._validate_tax_readiness(vehicle)
		self._validate_income_account()
		self._validate_sales_tax_template()
		self._set_status()
		return self.report

	def _new_report(self):
		return {key: [] if key in {"validations", "warnings", "blocking_errors"} else None for key in REPORT_KEYS} | {
			"status": "fail",
			"ready_to_create_sales_invoice_draft": False,
			"company": None,
			"taxes_and_charges": SALES_TAX_TEMPLATE,
			"tax_account": SALES_TAX_ACCOUNT,
		}

	def _find_latest_candidate_name(self):
		candidates = find_formal_sales_invoice_draft_readiness_candidates(limit=1)
		return candidates[0].get("vehicle") if candidates else None

	def _validate_vehicle(self, vehicle):
		self.report["vehicle_status"] = vehicle.get("status")
		self.report["formal_delivery_status"] = vehicle.get("formal_delivery_status")
		self.report["sales_invoice"] = vehicle.get("sales_invoice")
		self.report["item"] = vehicle.get("item")
		self.report["serial_no"] = vehicle.get("serial_no")

		if vehicle.get("status") != "已售出":
			self._block("車輛狀態必須是已售出。")
		if vehicle.get("sales_invoice"):
			self._block("此車輛已建立 Sales Invoice 草稿，不可重複建立。")
		if vehicle.get("formal_delivery_status") == "已完成":
			self._block("此車輛已完成正式交車入帳，不可重複建立 Sales Invoice 草稿。")
		if not vehicle.get("item"):
			self._block("車輛尚未建立 Item。")
		elif not frappe.db.exists("Item", vehicle.item):
			self._block(f"Item 不存在：{vehicle.item}")
		if not vehicle.get("serial_no"):
			self._block("車輛尚未建立 Serial No。")

		self.report["company"] = self._resolve_company(vehicle)
		self.report["warehouse"] = self._resolve_warehouse(vehicle)
		self._validate_warehouse()
		self.report["validations"].append("已完成 Used Car Vehicle 草稿建立 readiness 檢查。")

	def _resolve_company(self, vehicle):
		meta = frappe.get_meta("Used Car Vehicle")
		company = vehicle.get("company") if meta.has_field("company") and vehicle.get("company") else None
		company = company or frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		if not company:
			self._block("找不到公司，無法建立 Sales Invoice 草稿。")
			return None
		if company != COMPANY:
			self._block(f"正式 Sales Invoice 草稿 readiness 目前目標公司必須是 {COMPANY}，解析結果是 {company}。")
		elif not frappe.db.exists("Company", company):
			self._block(f"Company 不存在：{company}")
		return company

	def _resolve_warehouse(self, vehicle):
		meta = frappe.get_meta("Used Car Vehicle")
		for fieldname in ("warehouse", "target_warehouse", "source_warehouse", "stock_warehouse"):
			if meta.has_field(fieldname) and vehicle.get(fieldname):
				return vehicle.get(fieldname)

		if vehicle.get("stock_entry") and vehicle.get("item"):
			warehouse = frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": vehicle.stock_entry, "item_code": vehicle.item, "serial_no": ["like", f"%{vehicle.get('serial_no')}%"]},
				"t_warehouse",
				order_by="idx asc",
			)
			if not warehouse:
				warehouse = frappe.db.get_value(
					"Stock Entry Detail",
					{"parent": vehicle.stock_entry, "item_code": vehicle.item},
					"t_warehouse",
					order_by="idx asc",
				)
			if warehouse:
				return warehouse

		self._block("找不到車輛庫存倉，無法建立 Sales Invoice 草稿。")
		return None

	def _validate_warehouse(self):
		warehouse_name = self.report["warehouse"]
		company = self.report["company"]
		if not warehouse_name:
			return
		if not frappe.db.exists("Warehouse", warehouse_name):
			self._block(f"Warehouse 不存在：{warehouse_name}")
			return
		warehouse = frappe.get_doc("Warehouse", warehouse_name)
		if company and getattr(warehouse, "company", None) != company:
			self._block(f"Warehouse {warehouse_name} 不屬於公司 {company}。")
		if int(getattr(warehouse, "is_group", 0) or 0):
			self._block(f"Warehouse {warehouse_name} 是群組倉庫，不能用於 Sales Invoice。")
		if int(getattr(warehouse, "disabled", 0) or 0):
			self._block(f"Warehouse {warehouse_name} 已停用，不能用於 Sales Invoice。")

	def _resolve_completed_reservation(self, vehicle):
		reservation_name = vehicle.get("completed_reservation")
		if reservation_name and frappe.db.exists("Used Car Reservation", reservation_name):
			return frappe.get_doc("Used Car Reservation", reservation_name)

		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle.name, "status": "已完成"},
			"name",
			order_by="modified desc",
		)
		if reservation_name:
			if vehicle.get("completed_reservation") and not frappe.db.exists("Used Car Reservation", vehicle.completed_reservation):
				self._warn("vehicle.completed_reservation 指向不存在的保留單，已改用只讀查詢找到已完成保留單；未回填車輛。")
			return frappe.get_doc("Used Car Reservation", reservation_name)

		self._block("找不到已完成保留單。")
		return None

	def _validate_reservation(self, reservation):
		self.report["reservation"] = reservation.name
		self.report["reservation_status"] = reservation.get("status")
		self.report["customer"] = reservation.get("customer")
		if reservation.get("status") != "已完成":
			self._block("保留單狀態必須是已完成。")
		if not reservation.get("customer"):
			self._block("保留單缺少 Customer，無法建立 Sales Invoice 草稿。")
		elif not frappe.db.exists("Customer", reservation.customer):
			self._block(f"Customer 不存在：{reservation.customer}")
		self.report["validations"].append("已完成 Used Car Reservation readiness 檢查。")

	def _validate_completion_links(self, vehicle, reservation):
		for prefix, label, flow_type in (("deposit", "訂金", "訂金收款"), ("final", "尾款", "尾款收款")):
			money_field = f"{prefix}_money_flow"
			voucher_field = f"{prefix}_voucher_draft"
			journal_field = f"{prefix}_journal_entry"
			money_flow = vehicle.get(money_field)
			voucher_draft = vehicle.get(voucher_field)
			journal_entry = vehicle.get(journal_field)

			self.report[money_field] = money_flow
			self.report[voucher_field] = voucher_draft
			self.report[journal_field] = journal_entry
			self._warn_if_reservation_has_unbackfilled_link(reservation, vehicle, prefix, money_field, voucher_field, journal_field)

			if not money_flow:
				self._block(f"缺少{label}金流紀錄；需先經既有成交前檢查 / 成交確認流程補齊連結。")
				continue
			if not frappe.db.exists("Used Car Money Flow", money_flow):
				self._block(f"{label}金流紀錄不存在：{money_flow}")
				continue
			money_doc = frappe.get_doc("Used Car Money Flow", money_flow)
			self.report[f"{prefix}_money_flow_status"] = money_doc.get("status")
			if money_doc.get("status") != "已入帳":
				self._block(f"{label}金流尚未入帳。")
			if money_doc.get("flow_type") and money_doc.get("flow_type") != flow_type:
				self._block(f"{label}金流 flow_type 必須是 {flow_type}。")

			if not voucher_draft:
				self._block(f"缺少{label}傳票草稿；需先經既有成交前檢查 / 成交確認流程補齊連結。")
				continue
			if not frappe.db.exists("Used Car Voucher Draft", voucher_draft):
				self._block(f"{label}傳票草稿不存在：{voucher_draft}")
				continue
			voucher_doc = frappe.get_doc("Used Car Voucher Draft", voucher_draft)
			self.report[f"{prefix}_voucher_draft_status"] = voucher_doc.get("status")
			if voucher_doc.get("status") != "已入帳":
				self._block(f"{label}傳票草稿尚未入帳。")
			if not voucher_doc.get("journal_entry"):
				self._block(f"{label}傳票草稿缺少正式會計傳票。")
			elif voucher_doc.get("journal_entry") != journal_entry:
				self._block(f"{label}傳票草稿未連結車輛成交摘要的正式會計傳票。")

			if not journal_entry:
				self._block(f"缺少{label}正式會計傳票；需先經既有成交前檢查 / 成交確認流程補齊連結。")
			elif not frappe.db.exists("Journal Entry", journal_entry):
				self._block(f"{label}正式會計傳票不存在：{journal_entry}")
			else:
				journal_doc = frappe.get_doc("Journal Entry", journal_entry)
				if int(getattr(journal_doc, "docstatus", 0) or 0) != 1:
					self._warn(f"{label}正式會計傳票 docstatus 不是 1，建立草稿前需人工確認已提交。")

		self.report["validations"].append("已完成訂金 / 尾款金流、傳票草稿與 Journal Entry readiness 檢查。")

	def _warn_if_reservation_has_unbackfilled_link(self, reservation, vehicle, prefix, money_field, voucher_field, journal_field):
		reservation_fields = {
			money_field: "money_flow" if prefix == "deposit" else "final_money_flow",
			voucher_field: "voucher_draft" if prefix == "deposit" else "final_voucher_draft",
			journal_field: "journal_entry" if prefix == "deposit" else "final_journal_entry",
		}
		for vehicle_field, reservation_field in reservation_fields.items():
			if reservation.get(reservation_field) and not vehicle.get(vehicle_field):
				self._warn(f"reservation.{reservation_field} 有連結但 vehicle.{vehicle_field} 未回填；本 readiness 不回填資料。")

	def _resolve_sales_amount(self, reservation):
		final_payment_amount = reservation.get("final_payment_amount")
		if final_payment_amount is None and self.report.get("final_money_flow") and frappe.db.exists(
			"Used Car Money Flow", self.report["final_money_flow"]
		):
			final_payment_amount = frappe.get_doc("Used Car Money Flow", self.report["final_money_flow"]).get("amount")
		sales_amount = flt(reservation.get("deposit_amount")) + flt(final_payment_amount)
		self.report["sales_amount"] = sales_amount
		if sales_amount <= 0:
			self._block("Sales Invoice 草稿金額必須大於 0。")

	def _validate_tax_readiness(self, vehicle):
		tax_mode, review_status = derive_vehicle_tax_mode_from_purchase_document_type(vehicle.get("purchase_document_type"))
		self.report["vehicle_tax_mode"] = tax_mode
		self.report["tax_review_status"] = review_status
		if tax_mode == "待確認":
			self._block("買入憑證尚待會計確認，無法建立 Sales Invoice 草稿。")

	def _validate_income_account(self):
		item_code = self.report.get("item")
		company = self.report.get("company")
		if not item_code or not company or not frappe.db.exists("Item", item_code):
			return
		account = self._resolve_income_account(item_code, company)
		self.report["income_account"] = account

	def _resolve_income_account(self, item_code, company):
		item = frappe.get_doc("Item", item_code)
		for default in item.get("item_defaults") or []:
			if default.company == company and default.income_account:
				return self._validate_account(default.income_account, company, "收入科目")

		if item.get("item_group") and frappe.db.exists("Item Group", item.item_group):
			item_group = frappe.get_doc("Item Group", item.item_group)
			for default in item_group.get("item_defaults") or []:
				if default.company == company and default.income_account:
					return self._validate_account(default.income_account, company, "收入科目")

		if frappe.db.exists("Company", company):
			company_doc = frappe.get_doc("Company", company)
			if company_doc.get("default_income_account"):
				return self._validate_account(company_doc.default_income_account, company, "收入科目")

		fallback_account = frappe.db.get_value(
			"Account",
			{"company": company, "root_type": "Income", "is_group": 0, "disabled": 0},
			"name",
			order_by="name asc",
		)
		if fallback_account:
			return self._validate_account(fallback_account, company, "收入科目")

		self._block(f"找不到公司 {company} 可用的收入科目，無法建立 Sales Invoice 草稿。")
		return None

	def _validate_sales_tax_template(self):
		company = self.report.get("company")
		if not company:
			return
		if not frappe.db.exists("Sales Taxes and Charges Template", SALES_TAX_TEMPLATE):
			self._block(f"找不到 Sales Taxes and Charges Template：{SALES_TAX_TEMPLATE}。")
			return
		template = frappe.get_doc("Sales Taxes and Charges Template", SALES_TAX_TEMPLATE)
		if template.get("company") != company:
			self._block(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} 不屬於公司 {company}。")
		if int(template.get("disabled") or 0):
			self._block(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} 已停用。")
		taxes = list(template.get("taxes") or [])
		if len(taxes) != 1:
			self._block(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} 必須有且只有一筆稅項。")
			return
		row = taxes[0]
		if row.get("charge_type") != "On Net Total":
			self._block(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} charge_type 必須是 On Net Total。")
		if row.get("account_head") != SALES_TAX_ACCOUNT:
			self._block(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} account_head 必須是 {SALES_TAX_ACCOUNT}。")
		if flt(row.get("rate")) != SALES_TAX_RATE:
			self._block(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} rate 必須是 {SALES_TAX_RATE}。")
		if int(row.get("included_in_print_rate") or 0) != 1:
			self._block(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} included_in_print_rate 必須是 1。")
		self._validate_account(SALES_TAX_ACCOUNT, company, "銷項稅額科目")

	def _validate_account(self, account_name, company, label):
		if not account_name or not frappe.db.exists("Account", account_name):
			self._block(f"{label}不存在：{account_name}")
			return account_name
		account = frappe.get_doc("Account", account_name)
		if account.get("company") != company:
			self._block(f"{label} {account_name} 不屬於公司 {company}。")
		if int(account.get("is_group") or 0):
			self._block(f"{label} {account_name} 是群組科目，不能用於 Sales Invoice。")
		if int(account.get("disabled") or 0):
			self._block(f"{label} {account_name} 已停用，不能用於 Sales Invoice。")
		return account_name

	def _block(self, message):
		self.report["blocking_errors"].append(message)

	def _warn(self, message):
		self.report["warnings"].append(message)

	def _set_status(self):
		if self.report["blocking_errors"]:
			self.report["status"] = "fail"
		elif self.report["warnings"]:
			self.report["status"] = "warning"
		else:
			self.report["status"] = "pass"
		self.report["ready_to_create_sales_invoice_draft"] = self.report["status"] == "pass"


def _vehicle_candidate_filters():
	return {
		"status": "已售出",
		"sales_invoice": ["is", "not set"],
		"formal_delivery_status": ["!=", "已完成"],
	}


@frappe.whitelist()
def run_formal_sales_invoice_draft_readiness(vehicle_name=None):
	return FormalSalesInvoiceDraftReadinessService().run(vehicle_name=vehicle_name)


@frappe.whitelist()
def find_formal_sales_invoice_draft_readiness_candidates(limit=10):
	return frappe.db.get_all(
		"Used Car Vehicle",
		filters=_vehicle_candidate_filters(),
		fields=(
			"name as vehicle",
			"status as vehicle_status",
			"formal_delivery_status",
			"sales_invoice",
			"completed_reservation",
			"customer",
			"item",
			"serial_no",
			"stock_warehouse",
			"deposit_money_flow",
			"deposit_voucher_draft",
			"deposit_journal_entry",
			"final_money_flow",
			"final_voucher_draft",
			"final_journal_entry",
			"modified",
		),
		order_by="modified desc",
		limit=limit,
	)
