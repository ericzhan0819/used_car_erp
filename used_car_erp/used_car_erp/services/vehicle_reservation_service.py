import frappe
from frappe.utils import flt, now, nowdate

from used_car_erp.used_car_erp.services.used_car_action_permission_service import assert_can_perform_used_car_action
from used_car_erp.used_car_erp.services.used_car_controlled_write_service import (
	db_set_service_controlled_values,
	insert_service_controlled_doc,
	save_service_controlled_doc,
)
from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService
from used_car_erp.used_car_erp.services.vehicle_money_flow_service import VehicleMoneyFlowService
from used_car_erp.used_car_erp.doctype.used_car_vehicle.used_car_vehicle import (
	derive_vehicle_tax_mode_from_purchase_document_type,
)


VALID_PAYMENT_METHODS = ("現金", "匯款", "信用卡", "其他")
SALES_TAX_TEMPLATE = "台灣營業稅 5%（含稅） - O"
SALES_TAX_ACCOUNT = "0202134 - 銷項稅額 - O"
SALES_TAX_RATE = 5
RESTRICTED_ACCOUNTING_DOCTYPES = (
	"Stock Entry",
	"Purchase Invoice",
	"Sales Invoice",
	"Payment Entry",
	"Delivery Note",
	"Journal Entry",
)


class VehicleReservationService:
	def create_reservation(
		self,
		vehicle_name: str,
		customer_name: str,
		customer_phone: str,
		sold_price,
		deposit_amount,
		payment_method: str,
		deposit_date=None,
		payment_reference: str | None = None,
		notes: str | None = None,
		customer: str | None = None,
		cash_account: str | None = None,
		settlement_status: str | None = None,
	):
		assert_can_perform_used_car_action(
			"used_car_reservation.create",
			message="你沒有建立中古車保留單的權限。",
		)
		self._validate_customer_inputs(customer_name, customer_phone)
		self._validate_sale_amounts(sold_price, deposit_amount)
		self._validate_payment_method(payment_method)

		try:
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
			vehicle.check_permission("read")
			self._validate_vehicle_ready_for_reservation(vehicle)
			self._validate_no_active_reservation(vehicle.name)

			resolved_customer = customer or self._resolve_or_create_customer(customer_name, customer_phone)
			if not frappe.db.exists("Customer", resolved_customer):
				frappe.throw("指定的 ERPNext 客戶不存在。")

			previous_status = vehicle.status
			reservation_values = {
				"doctype": "Used Car Reservation",
				"vehicle": vehicle.name,
				"stock_no": vehicle.stock_no,
				"vehicle_title": self._vehicle_title(vehicle),
				"customer": resolved_customer,
				"customer_name": customer_name,
				"customer_phone": customer_phone,
				"deposit_amount": deposit_amount,
				"deposit_date": deposit_date or nowdate(),
				"payment_method": payment_method,
				"payment_reference": payment_reference,
				"notes": notes,
				"status": "有效",
				"created_by_service": 1,
			}
			reservation = insert_service_controlled_doc(
				frappe.get_doc(reservation_values),
				action="used_car_reservation.create",
				allowed_doctype="Used Car Reservation",
				fieldnames=reservation_values.keys(),
			)

			money_flow_result = VehicleMoneyFlowService().create_deposit_money_flow_from_reservation(
				reservation.name,
				cash_account=cash_account,
				settlement_status=settlement_status,
			)

			# 訂金保留只切換中古車業務狀態；正式會計傳票必須由傳票草稿人工確認後才建立。
			db_set_service_controlled_values(
				"Used Car Vehicle",
				vehicle.name,
				action="used_car_reservation.create",
				values={"status": "保留中", "sold_price": sold_price},
			)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"reservation": reservation.name,
			"money_flow": money_flow_result.get("money_flow"),
			"voucher_draft": money_flow_result.get("voucher_draft"),
			"vehicle_name": vehicle.name,
			"stock_no": vehicle.stock_no,
			"previous_status": previous_status,
			"status": "保留中",
			"customer": resolved_customer,
			"customer_name": customer_name,
			"customer_phone": customer_phone,
			"sold_price": flt(sold_price),
			"deposit_amount": flt(deposit_amount),
			"payment_method": payment_method,
			"changed": True,
			"message": "已建立訂金保留、金流紀錄與傳票草稿，車輛已改為保留中。",
		}

	def create_final_payment_for_active_reservation(
		self,
		vehicle_name: str,
		amount,
		payment_method: str,
		payment_date=None,
		payment_reference: str | None = None,
		notes: str | None = None,
		cash_account: str | None = None,
		settlement_status: str | None = None,
	):
		assert_can_perform_used_car_action(
			"used_car_money_flow.final_payment.create",
			message="你沒有建立中古車尾款金流的權限。",
		)
		self._validate_payment_method(payment_method)
		if flt(amount) <= 0:
			frappe.throw("尾款金額必須大於 0。")

		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle_name, "status": "有效"},
			"name",
			order_by="creation desc",
		)
		if not reservation_name:
			frappe.throw("找不到此車輛的有效保留紀錄。")

		try:
			result = VehicleMoneyFlowService().create_final_payment_money_flow_from_reservation(
				reservation_name=reservation_name,
				amount=amount,
				payment_method=payment_method,
				payment_date=payment_date,
				payment_reference=payment_reference,
				notes=notes,
				cash_account=cash_account,
				settlement_status=settlement_status,
			)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"reservation": reservation_name,
			"money_flow": result.get("money_flow"),
			"voucher_draft": result.get("voucher_draft"),
			"vehicle_name": vehicle_name,
			"amount": flt(amount),
			"changed": True,
			"message": "已建立尾款金流紀錄與傳票草稿，等待會計審核入帳。",
		}

	def preflight_delivery_for_active_reservation(self, vehicle_name: str):
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		vehicle.check_permission("read")
		if vehicle.status != "保留中":
			frappe.throw("車輛狀態不是保留中。")

		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle.name, "status": "有效"},
			"name",
			order_by="creation desc",
		)
		if not reservation_name:
			frappe.throw("找不到有效保留紀錄。")

		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.check_permission("read")
		deposit_money_flow = self._resolve_money_flow(reservation, "money_flow", "訂金收款")
		if not deposit_money_flow:
			frappe.throw("尚未建立訂金金流紀錄。")
		deposit_voucher_draft = self._resolve_voucher_draft(reservation, "voucher_draft", deposit_money_flow)
		if not deposit_voucher_draft:
			frappe.throw("尚未建立訂金傳票草稿。")

		deposit_journal_entry = self._validate_posted_accounting(
			deposit_money_flow,
			deposit_voucher_draft,
			"訂金",
		)
		final_money_flow = self._resolve_money_flow(reservation, "final_money_flow", "尾款收款")
		if not final_money_flow:
			frappe.throw("尚未建立尾款金流紀錄。")
		final_voucher_draft = self._resolve_voucher_draft(reservation, "final_voucher_draft", final_money_flow)
		if not final_voucher_draft:
			frappe.throw("尚未建立尾款傳票草稿。")

		final_journal_entry = self._validate_posted_accounting(final_money_flow, final_voucher_draft, "尾款")
		self._backfill_preflight_links(
			reservation,
			{
				"money_flow": deposit_money_flow,
				"voucher_draft": deposit_voucher_draft,
				"journal_entry": deposit_journal_entry,
				"final_money_flow": final_money_flow,
				"final_voucher_draft": final_voucher_draft,
				"final_journal_entry": final_journal_entry,
			},
		)

		return {
			"passed": True,
			"vehicle_name": vehicle.name,
			"reservation": reservation.name,
			"deposit_money_flow": deposit_money_flow,
			"deposit_voucher_draft": deposit_voucher_draft,
			"deposit_journal_entry": deposit_journal_entry,
			"final_money_flow": final_money_flow,
			"final_voucher_draft": final_voucher_draft,
			"final_journal_entry": final_journal_entry,
			"message": "此車輛已完成訂金與尾款入帳，可進入成交 / 交車流程。",
		}

	def preflight_formal_delivery_for_vehicle(self, vehicle_name: str):
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		vehicle.check_permission("read")

		if vehicle.status != "已售出":
			frappe.throw("車輛狀態不是已售出。")

		reservation = self._resolve_completed_reservation_for_vehicle(vehicle)
		reservation.check_permission("read")
		if reservation.status != "已完成":
			frappe.throw("保留單狀態不是已完成。")

		self._backfill_vehicle_completion_summary_from_reservation(vehicle, reservation)
		vehicle.reload()

		self._validate_formal_delivery_not_started(vehicle)
		self._validate_vehicle_completion_summary(vehicle)
		deposit_money_flow = self._validate_linked_money_flow(vehicle.deposit_money_flow, "訂金")
		final_money_flow = self._validate_linked_money_flow(vehicle.final_money_flow, "尾款")
		deposit_voucher_draft = self._validate_linked_voucher_draft(vehicle.deposit_voucher_draft, "訂金")
		final_voucher_draft = self._validate_linked_voucher_draft(vehicle.final_voucher_draft, "尾款")
		self._validate_linked_journal_entry(vehicle.deposit_journal_entry, "訂金")
		self._validate_linked_journal_entry(vehicle.final_journal_entry, "尾款")

		if deposit_money_flow.status != "已入帳":
			frappe.throw("訂金金流尚未入帳。")
		if final_money_flow.status != "已入帳":
			frappe.throw("尾款金流尚未入帳。")
		if deposit_voucher_draft.status != "已入帳":
			frappe.throw("訂金傳票草稿尚未入帳。")
		if final_voucher_draft.status != "已入帳":
			frappe.throw("尾款傳票草稿尚未入帳。")
		if not deposit_voucher_draft.journal_entry:
			frappe.throw("缺少訂金正式會計傳票。")
		if not final_voucher_draft.journal_entry:
			frappe.throw("缺少尾款正式會計傳票。")
		if deposit_voucher_draft.journal_entry != vehicle.deposit_journal_entry:
			frappe.throw("訂金傳票草稿未連結車輛成交摘要的正式會計傳票。")
		if final_voucher_draft.journal_entry != vehicle.final_journal_entry:
			frappe.throw("尾款傳票草稿未連結車輛成交摘要的正式會計傳票。")
		if not vehicle.item:
			frappe.throw("車輛尚未建立 Item。")
		if not vehicle.serial_no:
			frappe.throw("車輛尚未建立 Serial No。")

		return {
			"passed": True,
			"vehicle_name": vehicle.name,
			"reservation": reservation.name,
			"customer": reservation.customer,
			"item": vehicle.item,
			"serial_no": vehicle.serial_no,
			"deposit_money_flow": vehicle.deposit_money_flow,
			"deposit_voucher_draft": vehicle.deposit_voucher_draft,
			"deposit_journal_entry": vehicle.deposit_journal_entry,
			"final_money_flow": vehicle.final_money_flow,
			"final_voucher_draft": vehicle.final_voucher_draft,
			"final_journal_entry": vehicle.final_journal_entry,
			"sales_amount": self._resolve_formal_delivery_sales_amount(reservation, final_money_flow),
			"message": "此車輛已具備正式交車入帳前置條件，可進入 Sales Invoice 草稿建立階段。",
		}

	def create_sales_invoice_draft_for_vehicle(
		self,
		vehicle_name: str,
		posting_date=None,
		note: str | None = None,
	):
		preflight = self.preflight_formal_delivery_for_vehicle(vehicle_name)
		posting_date = posting_date or nowdate()

		try:
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
			vehicle.check_permission("read")
			reservation = frappe.get_doc("Used Car Reservation", preflight.get("reservation"))
			reservation.check_permission("read")

			if vehicle.status != "已售出":
				frappe.throw("車輛狀態不是已售出。")
			if reservation.status != "已完成":
				frappe.throw("保留單狀態不是已完成。")
			if vehicle.get("sales_invoice"):
				frappe.throw("此車輛已建立 Sales Invoice 草稿，不可重複建立。")
			if vehicle.get("formal_delivery_status") == "已完成":
				frappe.throw("此車輛已完成正式交車入帳，不可重複建立 Sales Invoice 草稿。")
			if not reservation.customer:
				frappe.throw("保留單缺少 Customer，無法建立 Sales Invoice 草稿。")
			tax_mode, tax_review_status = self._validate_purchase_evidence_for_sales_invoice_draft(vehicle)

			resolved_company = self._resolve_company_for_sales_invoice(vehicle)
			resolved_warehouse = self._resolve_vehicle_sales_warehouse(vehicle)
			resolved_income_account = self._resolve_sales_income_account(vehicle.item, resolved_company)
			tax_row = self._build_sales_tax_row_from_template(resolved_company)
			sales_amount = flt(preflight.get("sales_amount"))
			sales_invoice = frappe.get_doc(
				{
					"doctype": "Sales Invoice",
					"company": resolved_company,
					"customer": reservation.customer,
					"posting_date": posting_date,
					"due_date": posting_date,
					"update_stock": 1,
					"taxes_and_charges": SALES_TAX_TEMPLATE,
					"remarks": self._build_sales_invoice_draft_remarks(vehicle, reservation, tax_mode),
					"items": [
						{
							"item_code": vehicle.item,
							"qty": 1,
							"rate": sales_amount,
							"serial_no": vehicle.serial_no,
							"warehouse": resolved_warehouse,
							"income_account": resolved_income_account,
						}
					],
					"taxes": [tax_row],
				}
			).insert()

			self._write_vehicle_formal_delivery_draft(
				vehicle,
				{
					"formal_delivery_status": "銷售發票草稿",
					"formal_delivery_posting_date": posting_date,
					"sales_invoice": sales_invoice.name,
					"formal_delivery_note": note,
				},
			)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"vehicle_name": vehicle.name,
			"reservation": reservation.name,
			"sales_invoice": sales_invoice.name,
			"sales_invoice_status": "Draft",
			"formal_delivery_status": "銷售發票草稿",
			"sales_amount": sales_amount,
			"vehicle_tax_mode": tax_mode,
			"tax_review_status": tax_review_status,
			"taxes_and_charges": SALES_TAX_TEMPLATE,
			"tax_account": tax_row["account_head"],
			"message": "已建立 Sales Invoice 草稿，請先人工檢查後再進入正式提交與沖轉階段。",
		}

	def _validate_purchase_evidence_for_sales_invoice_draft(self, vehicle):
		purchase_document_type = vehicle.get("purchase_document_type")
		tax_mode, review_status = derive_vehicle_tax_mode_from_purchase_document_type(purchase_document_type)

		if tax_mode == "待確認":
			frappe.throw(
				"買入憑證尚待會計確認，無法建立 Sales Invoice 草稿。請先確認此車是否取得可扣抵統一發票，或是否適用 15-1。"
			)

		return tax_mode, review_status

	def _resolve_company_for_sales_invoice(self, vehicle):
		if frappe.get_meta("Used Car Vehicle").has_field("company") and vehicle.get("company"):
			return vehicle.company

		company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
		if not company:
			frappe.throw("找不到公司，無法建立 Sales Invoice 草稿。")
		return company

	def _resolve_sales_income_account(self, item_code: str, company: str):
		item = frappe.get_doc("Item", item_code)
		for default in item.get("item_defaults") or []:
			if default.company == company and default.income_account:
				return self._validate_account_for_company(default.income_account, company, "收入科目")

		if item.item_group:
			item_group = frappe.get_doc("Item Group", item.item_group)
			for default in item_group.get("item_defaults") or []:
				if default.company == company and default.income_account:
					return self._validate_account_for_company(default.income_account, company, "收入科目")

		if not frappe.db.exists("Company", company):
			frappe.throw(f"找不到公司 {company}，無法建立 Sales Invoice 草稿。")

		company_doc = frappe.get_doc("Company", company)
		if company_doc.get("default_income_account"):
			return self._validate_account_for_company(company_doc.default_income_account, company, "收入科目")

		fallback_account = frappe.db.get_value(
			"Account",
			{
				"company": company,
				"root_type": "Income",
				"is_group": 0,
				"disabled": 0,
			},
			"name",
			order_by="name asc",
		)
		if fallback_account:
			return self._validate_account_for_company(fallback_account, company, "收入科目")

		frappe.throw(
			f"找不到公司 {company} 可用的收入科目，無法建立 Sales Invoice 草稿。請先設定 Item、Item Group 或 Company 的 income account。"
		)

	def _validate_account_for_company(self, account: str, company: str, label: str):
		account_doc = frappe.get_doc("Account", account) if frappe.db.exists("Account", account) else None
		if not account_doc:
			frappe.throw(f"{label} {account} 不存在。")
		if account_doc.company != company:
			frappe.throw(f"{label} {account} 不屬於公司 {company}。")
		if account_doc.is_group:
			frappe.throw(f"{label} {account} 是群組科目，不能用於 Sales Invoice。")
		if account_doc.disabled:
			frappe.throw(f"{label} {account} 已停用，不能用於 Sales Invoice。")
		return account

	def _build_sales_tax_row_from_template(self, company: str):
		template, row = self._resolve_sales_tax_template(company)
		return {
			"charge_type": row.charge_type,
			"account_head": row.account_head,
			"rate": row.rate,
			"included_in_print_rate": row.included_in_print_rate,
			"description": getattr(row, "description", None) or "營業稅 5%（含稅）",
		}

	def _resolve_sales_tax_template(self, company: str):
		if not frappe.db.exists("Sales Taxes and Charges Template", SALES_TAX_TEMPLATE):
			frappe.throw(f"找不到 Sales Taxes and Charges Template：{SALES_TAX_TEMPLATE}。")

		template = frappe.get_doc("Sales Taxes and Charges Template", SALES_TAX_TEMPLATE)
		if template.company != company:
			frappe.throw(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} 不屬於公司 {company}。")
		if int(getattr(template, "disabled", 0) or 0):
			frappe.throw(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} 已停用。")

		taxes = list(getattr(template, "taxes", []) or [])
		if len(taxes) != 1:
			frappe.throw(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} 必須有且只有一筆稅項。")

		row = taxes[0]
		if row.charge_type != "On Net Total":
			frappe.throw(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} charge_type 必須是 On Net Total。")
		if row.account_head != SALES_TAX_ACCOUNT:
			frappe.throw(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} account_head 必須是 {SALES_TAX_ACCOUNT}。")
		if flt(row.rate) != SALES_TAX_RATE:
			frappe.throw(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} rate 必須是 {SALES_TAX_RATE}。")
		if int(getattr(row, "included_in_print_rate", 0) or 0) != 1:
			frappe.throw(f"Sales Taxes and Charges Template {SALES_TAX_TEMPLATE} included_in_print_rate 必須是 1。")

		self._validate_account_for_company(SALES_TAX_ACCOUNT, company, "銷項稅額科目")
		return template, row

	def complete_active_reservation(self, vehicle_name: str, completion_note: str | None = None):
		assert_can_perform_used_car_action(
			"used_car_reservation.complete_sale",
			message="你沒有確認中古車成交的權限。",
		)
		preflight = self.preflight_delivery_for_active_reservation(vehicle_name)

		try:
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
			vehicle.check_permission("write")
			if vehicle.status != "保留中":
				frappe.throw("車輛狀態不是保留中。")

			reservation_name = frappe.db.get_value(
				"Used Car Reservation",
				{"vehicle": vehicle.name, "status": "有效"},
				"name",
				order_by="creation desc",
			)
			if not reservation_name:
				frappe.throw("找不到有效保留紀錄。")

			reservation = frappe.get_doc("Used Car Reservation", reservation_name)
			reservation.check_permission("read")
			if reservation.status != "有效":
				frappe.throw("保留紀錄不是有效狀態。")

			previous_vehicle_status = vehicle.status
			completed_at = now()
			completed_by = frappe.session.user
			self._write_vehicle_sale_completion_summary(
				vehicle,
				{
					"status": "已售出",
					"completed_reservation": reservation.name,
					"completed_at": completed_at,
					"completed_by": completed_by,
					"completion_note": completion_note,
					"deposit_money_flow": preflight.get("deposit_money_flow"),
					"deposit_voucher_draft": preflight.get("deposit_voucher_draft"),
					"deposit_journal_entry": preflight.get("deposit_journal_entry"),
					"final_money_flow": preflight.get("final_money_flow"),
					"final_voucher_draft": preflight.get("final_voucher_draft"),
					"final_journal_entry": preflight.get("final_journal_entry"),
				},
			)
			# 成交確認只回寫業務狀態，不建立或異動 ERPNext 會計、銷售與庫存文件。
			reservation.flags.ignore_accounting_link_validation = True
			save_service_controlled_doc(
				reservation,
				action="used_car_reservation.complete_sale",
				allowed_doctype="Used Car Reservation",
				values={
					"status": "已完成",
					"completed_at": completed_at,
					"completed_by": completed_by,
					"completion_note": completion_note,
				},
			)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"vehicle_name": vehicle.name,
			"reservation": reservation.name,
			"previous_vehicle_status": previous_vehicle_status,
			"vehicle_status": "已售出",
			"reservation_status": "已完成",
			"completed_at": reservation.completed_at,
			"completed_by": reservation.completed_by,
			"message": "已確認成交，車輛已標記為已售出。",
		}

	def cancel_reservation(self, reservation_name: str, reason: str):
		assert_can_perform_used_car_action(
			"used_car_reservation.cancel",
			message="你沒有取消中古車保留單的權限。",
		)
		if not reason:
			frappe.throw("取消原因為必填。")

		try:
			reservation = frappe.get_doc("Used Car Reservation", reservation_name)
			reservation.check_permission("read")
			if reservation.status != "有效":
				frappe.throw("只有有效的保留可以取消。")

			vehicle = frappe.get_doc("Used Car Vehicle", reservation.vehicle)
			vehicle.check_permission("read")
			previous_status = vehicle.status

			# 取消資訊由 service 寫入，避免使用者直接改狀態造成保留與車輛狀態不一致。
			reservation.flags.ignore_accounting_link_validation = True
			save_service_controlled_doc(
				reservation,
				action="used_car_reservation.cancel",
				allowed_doctype="Used Car Reservation",
				values={
					"status": "已取消",
					"cancellation_reason": reason,
					"cancelled_at": now(),
					"cancelled_by": frappe.session.user,
				},
			)

			if vehicle.status == "保留中":
				db_set_service_controlled_values(
					"Used Car Vehicle",
					vehicle.name,
					action="used_car_reservation.cancel",
					values={"status": "上架中"},
				)
				status = "上架中"
			else:
				status = vehicle.status

			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"reservation": reservation.name,
			"vehicle_name": vehicle.name,
			"previous_status": previous_status,
			"status": status,
			"reservation_status": "已取消",
			"changed": True,
			"message": "已取消保留，車輛已回到上架中。",
		}

	def cancel_active_reservation_for_vehicle(self, vehicle_name: str, reason: str):
		assert_can_perform_used_car_action(
			"used_car_reservation.cancel",
			message="你沒有取消中古車保留單的權限。",
		)
		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle_name, "status": "有效"},
			"name",
			order_by="creation desc",
		)
		if not reservation_name:
			frappe.throw("找不到此車輛的有效保留紀錄。")

		return self.cancel_reservation(reservation_name, reason)

	def cancel_active_reservation_with_deposit_handling(
		self,
		vehicle_name: str,
		reason: str,
		refund_payment_method: str | None = None,
		refund_date=None,
		refund_reference: str | None = None,
		refund_notes: str | None = None,
	):
		assert_can_perform_used_car_action(
			"used_car_reservation.cancel_with_deposit_handling",
			message="你沒有取消中古車保留單的權限。",
		)
		if not reason:
			frappe.throw("取消原因為必填。")

		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle_name, "status": "有效"},
			"name",
			order_by="creation desc",
		)
		if not reservation_name:
			frappe.throw("找不到此車輛的有效保留紀錄。")

		try:
			reservation = frappe.get_doc("Used Car Reservation", reservation_name)
			reservation.check_permission("read")
			vehicle = frappe.get_doc("Used Car Vehicle", reservation.vehicle)
			vehicle.check_permission("read")
			previous_status = vehicle.status

			if vehicle.status != "保留中":
				frappe.throw("車輛狀態不是保留中。")
			if reservation.final_money_flow or reservation.final_voucher_draft or reservation.final_journal_entry:
				frappe.throw("此車已記錄尾款，請先由管理者或會計處理後再取消。")

			deposit_money_flow = self._resolve_money_flow(reservation, "money_flow", "訂金收款")
			deposit_voucher_draft = self._resolve_voucher_draft(reservation, "voucher_draft", deposit_money_flow) if deposit_money_flow else None
			deposit_is_posted = self._is_deposit_posted(reservation, deposit_money_flow, deposit_voucher_draft)
			refund_result = None

			if deposit_is_posted:
				if not refund_payment_method:
					frappe.throw("退款方式為必填。")
				refund_result = VehicleMoneyFlowService().create_deposit_refund_money_flow_from_reservation(
					reservation_name=reservation.name,
					refund_payment_method=refund_payment_method,
					refund_date=refund_date,
					refund_reference=refund_reference,
					refund_notes=refund_notes,
				)
			else:
				self._void_unposted_deposit_documents(deposit_money_flow, deposit_voucher_draft, reason)

			cancelled_at = now()
			reservation.flags.ignore_accounting_link_validation = True
			save_service_controlled_doc(
				reservation,
				action="used_car_reservation.cancel_with_deposit_handling",
				allowed_doctype="Used Car Reservation",
				values={
					"status": "已取消",
					"cancellation_reason": reason,
					"cancelled_at": cancelled_at,
					"cancelled_by": frappe.session.user,
				},
			)
			db_set_service_controlled_values(
				"Used Car Vehicle",
				vehicle.name,
				action="used_car_reservation.cancel_with_deposit_handling",
				values={"status": "上架中"},
			)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"reservation": reservation.name,
			"vehicle_name": vehicle.name,
			"previous_status": previous_status,
			"vehicle_status": "上架中",
			"reservation_status": "已取消",
			"refund_required": bool(deposit_is_posted),
			"refund_money_flow": refund_result.get("money_flow") if refund_result else None,
			"refund_voucher_draft": refund_result.get("voucher_draft") if refund_result else None,
			"changed": True,
			"message": "已取消保留。",
		}

	def get_active_reservation_for_vehicle(self, vehicle_name: str):
		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle_name, "status": "有效"},
			"name",
			order_by="creation desc",
		)
		if not reservation_name:
			return None

		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.check_permission("read")
		deposit_status = self._build_reservation_flow_status_payload(
			reservation,
			money_flow_field="money_flow",
			voucher_draft_field="voucher_draft",
			flow_type="訂金收款",
		)
		final_status = self._build_reservation_flow_status_payload(
			reservation,
			money_flow_field="final_money_flow",
			voucher_draft_field="final_voucher_draft",
			flow_type="尾款收款",
		)
		return {
			"reservation": reservation.name,
			"customer": reservation.customer,
			"customer_name": reservation.customer_name,
			"customer_phone": reservation.customer_phone,
			"deposit_amount": reservation.deposit_amount,
			"payment_method": reservation.payment_method,
			"deposit_date": reservation.deposit_date,
			"money_flow": deposit_status["money_flow"],
			"voucher_draft": deposit_status["voucher_draft"],
			"journal_entry": deposit_status["journal_entry"],
			"deposit_status": deposit_status["status"],
			"final_money_flow": final_status["money_flow"],
			"final_voucher_draft": final_status["voucher_draft"],
			"final_journal_entry": final_status["journal_entry"],
			"final_payment_amount": reservation.get("final_payment_amount"),
			"final_payment_date": reservation.get("final_payment_date"),
			"final_payment_method": reservation.get("final_payment_method"),
			"final_status": final_status["status"],
		}

	def _build_reservation_flow_status_payload(
		self,
		reservation,
		*,
		money_flow_field: str,
		voucher_draft_field: str,
		flow_type: str,
	):
		money_flow = self._resolve_money_flow(reservation, money_flow_field, flow_type)
		voucher_draft = self._resolve_voucher_draft(reservation, voucher_draft_field, money_flow) if money_flow else None
		journal_entry = self._resolve_posted_journal_entry_for_status(money_flow, voucher_draft)

		return {
			"money_flow": money_flow,
			"voucher_draft": voucher_draft,
			"journal_entry": journal_entry,
			"status": self._format_reservation_flow_status(money_flow, voucher_draft, journal_entry),
		}

	def _resolve_posted_journal_entry_for_status(self, money_flow_name: str | None, voucher_draft_name: str | None):
		if not money_flow_name and not voucher_draft_name:
			return None

		journal_entry = None

		if voucher_draft_name and frappe.db.exists("Used Car Voucher Draft", voucher_draft_name):
			journal_entry = frappe.db.get_value("Used Car Voucher Draft", voucher_draft_name, "journal_entry")

		if not journal_entry and money_flow_name and frappe.db.exists("Used Car Money Flow", money_flow_name):
			journal_entry = frappe.db.get_value("Used Car Money Flow", money_flow_name, "journal_entry")

		if journal_entry and frappe.db.exists("Journal Entry", journal_entry):
			return journal_entry

		return None

	def _is_deposit_posted(self, reservation, money_flow_name: str | None, voucher_draft_name: str | None):
		if reservation.get("journal_entry"):
			return True
		if money_flow_name and frappe.db.exists("Used Car Money Flow", money_flow_name):
			money_flow = frappe.get_doc("Used Car Money Flow", money_flow_name)
			if money_flow.status == "已入帳" or money_flow.journal_entry:
				return True
		if voucher_draft_name and frappe.db.exists("Used Car Voucher Draft", voucher_draft_name):
			voucher_draft = frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)
			if voucher_draft.status == "已入帳" or voucher_draft.journal_entry:
				return True
		return False

	def _void_unposted_deposit_documents(self, money_flow_name: str | None, voucher_draft_name: str | None, reason: str):
		if voucher_draft_name and frappe.db.exists("Used Car Voucher Draft", voucher_draft_name):
			voucher_draft = frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)
			if voucher_draft.status in ("待審核", "已退回"):
				if voucher_draft.journal_entry:
					frappe.throw("訂金已完成內部確認，請改走退款處理。")
				save_service_controlled_doc(
					voucher_draft,
					action="used_car_reservation.cancel_with_deposit_handling",
					allowed_doctype="Used Car Voucher Draft",
					values={
						"status": "已作廢",
						"reviewed_by": frappe.session.user,
						"reviewed_at": now(),
						"review_note": reason,
					},
				)
			elif voucher_draft.status != "已作廢":
				frappe.throw("訂金已完成內部確認，請改走退款處理。")

		if money_flow_name and frappe.db.exists("Used Car Money Flow", money_flow_name):
			money_flow = frappe.get_doc("Used Car Money Flow", money_flow_name)
			if money_flow.status in ("待審核", "已作廢"):
				db_set_service_controlled_values(
					"Used Car Money Flow",
					money_flow.name,
					action="used_car_reservation.cancel_with_deposit_handling",
					values={"status": "已作廢"},
				)
			elif money_flow.status != "已作廢":
				frappe.throw("訂金已完成內部確認，請改走退款處理。")

	def _format_reservation_flow_status(self, money_flow_name, voucher_draft_name, journal_entry_name):
		if journal_entry_name:
			return "已入帳"
		if voucher_draft_name:
			return "傳票草稿"
		if money_flow_name:
			return "已記錄金流"
		return "未記錄"

	def _resolve_completed_reservation_for_vehicle(self, vehicle):
		reservation_name = vehicle.get("completed_reservation")
		if reservation_name and frappe.db.exists("Used Car Reservation", reservation_name):
			return frappe.get_doc("Used Car Reservation", reservation_name)

		reservation_name = frappe.db.get_value(
			"Used Car Reservation",
			{"vehicle": vehicle.name, "status": "已完成"},
			"name",
			order_by="modified desc",
		)
		if not reservation_name:
			frappe.throw("找不到已完成保留單。")
		return frappe.get_doc("Used Car Reservation", reservation_name)

	def _backfill_vehicle_completion_summary_from_reservation(self, vehicle, reservation):
		meta = frappe.get_meta("Used Car Vehicle")
		fields = (
			"completed_reservation",
			"completed_at",
			"completed_by",
			"completion_note",
			"deposit_money_flow",
			"deposit_voucher_draft",
			"deposit_journal_entry",
			"final_money_flow",
			"final_voucher_draft",
			"final_journal_entry",
		)
		if all(not meta.has_field(fieldname) or vehicle.get(fieldname) for fieldname in fields):
			return

		deposit_money_flow = self._resolve_money_flow(reservation, "money_flow", "訂金收款")
		if not deposit_money_flow:
			frappe.throw("缺少訂金金流紀錄。")
		deposit_voucher_draft = self._resolve_voucher_draft(reservation, "voucher_draft", deposit_money_flow)
		if not deposit_voucher_draft:
			frappe.throw("缺少訂金傳票草稿。")
		deposit_journal_entry = self._validate_posted_accounting(deposit_money_flow, deposit_voucher_draft, "訂金")

		final_money_flow = self._resolve_money_flow(reservation, "final_money_flow", "尾款收款")
		if not final_money_flow:
			frappe.throw("缺少尾款金流紀錄。")
		final_voucher_draft = self._resolve_voucher_draft(reservation, "final_voucher_draft", final_money_flow)
		if not final_voucher_draft:
			frappe.throw("缺少尾款傳票草稿。")
		final_journal_entry = self._validate_posted_accounting(final_money_flow, final_voucher_draft, "尾款")

		self._write_vehicle_sale_completion_summary(
			vehicle,
			{
				"completed_reservation": reservation.name,
				"completed_at": reservation.get("completed_at"),
				"completed_by": reservation.get("completed_by"),
				"completion_note": reservation.get("completion_note"),
				"deposit_money_flow": deposit_money_flow,
				"deposit_voucher_draft": deposit_voucher_draft,
				"deposit_journal_entry": deposit_journal_entry,
				"final_money_flow": final_money_flow,
				"final_voucher_draft": final_voucher_draft,
				"final_journal_entry": final_journal_entry,
			},
		)
		frappe.db.commit()

	def _resolve_money_flow(self, reservation, link_field: str, flow_type: str):
		linked_money_flow = reservation.get(link_field)
		if linked_money_flow and self._money_flow_matches(linked_money_flow, reservation.name, flow_type):
			return linked_money_flow

		return frappe.db.get_value(
			"Used Car Money Flow",
			{"reservation": reservation.name, "flow_type": flow_type, "status": ["!=", "已作廢"]},
			"name",
			order_by="creation desc",
		)

	def _money_flow_matches(self, money_flow_name: str, reservation_name: str, flow_type: str):
		return bool(
			frappe.db.exists(
				"Used Car Money Flow",
				{"name": money_flow_name, "reservation": reservation_name, "flow_type": flow_type, "status": ["!=", "已作廢"]},
			)
		)

	def _resolve_voucher_draft(self, reservation, link_field: str, money_flow_name: str):
		linked_voucher_draft = reservation.get(link_field)
		if linked_voucher_draft and self._voucher_draft_matches(linked_voucher_draft, reservation.name, money_flow_name):
			return linked_voucher_draft

		voucher_draft = frappe.db.get_value(
			"Used Car Voucher Draft",
			{"money_flow": money_flow_name, "status": ["!=", "已作廢"]},
			"name",
			order_by="creation desc",
		)
		if voucher_draft:
			return voucher_draft

		return frappe.db.get_value(
			"Used Car Voucher Draft",
			{"reservation": reservation.name, "status": ["!=", "已作廢"]},
			"name",
			order_by="creation desc",
		)

	def _voucher_draft_matches(self, voucher_draft_name: str, reservation_name: str, money_flow_name: str):
		return bool(
			frappe.db.exists(
				"Used Car Voucher Draft",
				{
					"name": voucher_draft_name,
					"reservation": reservation_name,
					"money_flow": money_flow_name,
					"status": ["!=", "已作廢"],
				},
			)
		)

	def _validate_posted_accounting(self, money_flow_name: str, voucher_draft_name: str, label: str):
		money_flow = frappe.get_doc("Used Car Money Flow", money_flow_name)
		voucher_draft = frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)
		if money_flow.status != "已入帳":
			frappe.throw(f"{label}金流尚未入帳。")
		if voucher_draft.status != "已入帳" or not voucher_draft.journal_entry:
			frappe.throw(f"{label}傳票尚未入帳。")
		return voucher_draft.journal_entry

	def _backfill_preflight_links(self, reservation, links: dict):
		updates = {}
		reservation_meta = frappe.get_meta("Used Car Reservation")
		for fieldname, value in links.items():
			if reservation_meta.has_field(fieldname) and value and not reservation.get(fieldname):
				updates[fieldname] = value
		if not updates:
			return

		# 成交前檢查只修復已存在且相符的會計連結，避免繞過 DocType 對人工改帳連結的保護。
		reservation.flags.ignore_accounting_link_validation = True
		for fieldname, value in updates.items():
			reservation.set(fieldname, value)
		reservation.save()

	def _validate_formal_delivery_not_started(self, vehicle):
		meta = frappe.get_meta("Used Car Vehicle")
		for fieldname, label in (
			("sales_invoice", "Sales Invoice"),
			("advance_settlement_journal_entry", "預收款沖轉 Journal Entry"),
		):
			if meta.has_field(fieldname) and vehicle.get(fieldname):
				frappe.throw(f"此車輛已建立 {label}，不可重複進行正式交車入帳。")
		if meta.has_field("formal_delivery_status") and vehicle.get("formal_delivery_status") == "已完成":
			frappe.throw("此車輛已完成正式交車入帳，不可重複進行正式交車入帳。")

	def _validate_vehicle_completion_summary(self, vehicle):
		for fieldname, message in (
			("deposit_money_flow", "缺少訂金金流紀錄。"),
			("deposit_voucher_draft", "缺少訂金傳票草稿。"),
			("deposit_journal_entry", "缺少訂金正式會計傳票。"),
			("final_money_flow", "缺少尾款金流紀錄。"),
			("final_voucher_draft", "缺少尾款傳票草稿。"),
			("final_journal_entry", "缺少尾款正式會計傳票。"),
		):
			if not vehicle.get(fieldname):
				frappe.throw(message)

	def _validate_linked_money_flow(self, money_flow_name: str, label: str):
		if not money_flow_name or not frappe.db.exists("Used Car Money Flow", money_flow_name):
			frappe.throw(f"缺少{label}金流紀錄。")
		return frappe.get_doc("Used Car Money Flow", money_flow_name)

	def _validate_linked_voucher_draft(self, voucher_draft_name: str, label: str):
		if not voucher_draft_name or not frappe.db.exists("Used Car Voucher Draft", voucher_draft_name):
			frappe.throw(f"缺少{label}傳票草稿。")
		return frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)

	def _validate_linked_journal_entry(self, journal_entry_name: str, label: str):
		if not journal_entry_name or not frappe.db.exists("Journal Entry", journal_entry_name):
			frappe.throw(f"缺少{label}正式會計傳票。")

	def _resolve_formal_delivery_sales_amount(self, reservation, final_money_flow):
		final_payment_amount = reservation.get("final_payment_amount")
		if final_payment_amount is None:
			final_payment_amount = final_money_flow.amount
		return flt(reservation.deposit_amount) + flt(final_payment_amount)

	def _resolve_vehicle_sales_warehouse(self, vehicle):
		meta = frappe.get_meta("Used Car Vehicle")
		for fieldname in ("warehouse", "target_warehouse", "source_warehouse", "stock_warehouse"):
			if meta.has_field(fieldname) and vehicle.get(fieldname):
				return vehicle.get(fieldname)

		if vehicle.get("stock_entry"):
			warehouse = frappe.db.get_value(
				"Stock Entry Detail",
				{"parent": vehicle.stock_entry, "item_code": vehicle.item, "serial_no": ["like", f"%{vehicle.serial_no}%"]},
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

		frappe.throw("找不到車輛庫存倉，無法建立 Sales Invoice 草稿。")

	def _build_sales_invoice_draft_remarks(self, vehicle, reservation, tax_mode=None):
		return "\n".join(
			str(part)
			for part in (
				"中古車正式銷售草稿",
				f"車輛：{vehicle.name}",
				f"庫存編號：{vehicle.stock_no}",
				f"保留單：{reservation.name}",
				f"中古車稅務判斷：{tax_mode}" if tax_mode else None,
				f"訂金金流：{vehicle.deposit_money_flow}",
				f"尾款金流：{vehicle.final_money_flow}",
			)
			if part
		)

	def _write_vehicle_formal_delivery_draft(self, vehicle, values: dict):
		meta = frappe.get_meta("Used Car Vehicle")
		vehicle.flags.ignore_formal_delivery_validation = True
		for fieldname, value in values.items():
			if meta.has_field(fieldname):
				vehicle.set(fieldname, value)
		vehicle.save()

	def _write_vehicle_sale_completion_summary(self, vehicle, values: dict):
		meta = frappe.get_meta("Used Car Vehicle")
		vehicle.flags.ignore_sale_completion_validation = True
		controlled_values = {}
		for fieldname, value in values.items():
			if fieldname == "status" or (meta.has_field(fieldname) and value):
				controlled_values[fieldname] = value
		if controlled_values:
			save_service_controlled_doc(
				vehicle,
				action="used_car_reservation.complete_sale",
				allowed_doctype="Used Car Vehicle",
				values=controlled_values,
			)

	def _validate_vehicle_ready_for_reservation(self, vehicle):
		if not vehicle.item or not vehicle.serial_no or not vehicle.stock_entry:
			frappe.throw("車輛必須完成入庫後，才能建立訂金保留。")
		if vehicle.status != "上架中":
			frappe.throw("只有上架中車輛可以建立訂金保留。")

	def _validate_no_active_reservation(self, vehicle_name: str):
		if frappe.db.exists("Used Car Reservation", {"vehicle": vehicle_name, "status": "有效"}):
			frappe.throw("此車輛已有有效保留紀錄，不可重複建立。")

	def _validate_customer_inputs(self, customer_name: str, customer_phone: str):
		if not customer_name:
			frappe.throw("客戶姓名為必填。")
		if not customer_phone:
			frappe.throw("客戶電話為必填。")

	def _validate_sale_amounts(self, sold_price, deposit_amount):
		if flt(sold_price) <= 0:
			frappe.throw("成交價必須大於 0。")
		if flt(deposit_amount) <= 0:
			frappe.throw("訂金金額必須大於 0。")
		if flt(deposit_amount) > flt(sold_price):
			frappe.throw("訂金不能大於成交價。")

	def _validate_payment_method(self, payment_method: str):
		if payment_method not in VALID_PAYMENT_METHODS:
			frappe.throw("付款方式必須是：現金、匯款、信用卡、其他。")

	def _resolve_or_create_customer(self, customer_name: str, customer_phone: str):
		customer_meta = frappe.get_meta("Customer")
		for phone_field in ("mobile_no", "phone"):
			if customer_meta.has_field(phone_field):
				customer = frappe.db.get_value("Customer", {phone_field: customer_phone}, "name")
				if customer:
					return customer

		customer = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
		if customer:
			return customer

		customer_doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_type": "Individual",
				"customer_group": self._resolve_customer_group(),
				"territory": self._resolve_territory(),
			}
		)
		if customer_meta.has_field("mobile_no"):
			customer_doc.mobile_no = customer_phone
		elif customer_meta.has_field("phone"):
			customer_doc.phone = customer_phone

		# 只建立 Customer 主檔，不建立 Address / Contact / Payment，避免訂金紀錄誤變正式收款流程。
		customer_doc.insert()
		return customer_doc.name

	def _resolve_customer_group(self):
		for group_name in ("Individual", "個人"):
			if frappe.db.exists("Customer Group", {"name": group_name, "is_group": 0}):
				return group_name

		customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name", order_by="name asc")
		if not customer_group:
			frappe.throw("找不到可用的非群組 Customer Group，無法建立 ERPNext Customer。")
		return customer_group

	def _resolve_territory(self):
		for territory_name in ("Taiwan", "台灣"):
			if frappe.db.exists("Territory", {"name": territory_name, "is_group": 0}):
				return territory_name

		territory = frappe.db.get_value("Territory", {"is_group": 0}, "name", order_by="name asc")
		if not territory:
			frappe.throw("找不到可用的非群組 Territory，無法建立 ERPNext Customer。")
		return territory

	def _vehicle_title(self, vehicle):
		return " ".join(str(part) for part in (vehicle.year, vehicle.brand, vehicle.model) if part)


@frappe.whitelist()
def create_reservation(
	vehicle_name: str,
	customer_name: str,
	customer_phone: str,
	sold_price,
	deposit_amount,
	payment_method: str,
	deposit_date=None,
	payment_reference: str | None = None,
	notes: str | None = None,
	customer: str | None = None,
	cash_account: str | None = None,
	settlement_status: str | None = None,
):
	service = VehicleReservationService()
	return service.create_reservation(
		vehicle_name=vehicle_name,
		customer_name=customer_name,
		customer_phone=customer_phone,
		sold_price=sold_price,
		deposit_amount=deposit_amount,
		payment_method=payment_method,
		deposit_date=deposit_date,
		payment_reference=payment_reference,
		notes=notes,
		customer=customer,
		cash_account=cash_account,
		settlement_status=settlement_status,
	)


@frappe.whitelist()
def create_final_payment_for_active_reservation(
	vehicle_name: str,
	amount,
	payment_method: str,
	payment_date=None,
	payment_reference: str | None = None,
	notes: str | None = None,
	cash_account: str | None = None,
	settlement_status: str | None = None,
):
	service = VehicleReservationService()
	return service.create_final_payment_for_active_reservation(
		vehicle_name=vehicle_name,
		amount=amount,
		payment_method=payment_method,
		payment_date=payment_date,
		payment_reference=payment_reference,
		notes=notes,
		cash_account=cash_account,
		settlement_status=settlement_status,
	)


@frappe.whitelist()
def preflight_delivery_for_active_reservation(vehicle_name: str):
	service = VehicleReservationService()
	return service.preflight_delivery_for_active_reservation(vehicle_name)


@frappe.whitelist()
def preflight_formal_delivery_for_vehicle(vehicle_name: str):
	service = VehicleReservationService()
	return service.preflight_formal_delivery_for_vehicle(vehicle_name)


@frappe.whitelist()
def create_sales_invoice_draft_for_vehicle(
	vehicle_name: str,
	posting_date=None,
	note: str | None = None,
):
	service = VehicleReservationService()
	return service.create_sales_invoice_draft_for_vehicle(
		vehicle_name=vehicle_name,
		posting_date=posting_date,
		note=note,
	)


@frappe.whitelist()
def complete_active_reservation(vehicle_name: str, completion_note: str | None = None):
	service = VehicleReservationService()
	return service.complete_active_reservation(vehicle_name, completion_note)


@frappe.whitelist()
def cancel_reservation(reservation_name: str, reason: str):
	service = VehicleReservationService()
	return service.cancel_reservation(reservation_name, reason)


@frappe.whitelist()
def cancel_active_reservation_for_vehicle(vehicle_name: str, reason: str):
	service = VehicleReservationService()
	return service.cancel_active_reservation_for_vehicle(vehicle_name, reason)


@frappe.whitelist()
def cancel_active_reservation_with_deposit_handling(
	vehicle_name: str,
	reason: str,
	refund_payment_method: str | None = None,
	refund_date=None,
	refund_reference: str | None = None,
	refund_notes: str | None = None,
):
	service = VehicleReservationService()
	return service.cancel_active_reservation_with_deposit_handling(
		vehicle_name=vehicle_name,
		reason=reason,
		refund_payment_method=refund_payment_method,
		refund_date=refund_date,
		refund_reference=refund_reference,
		refund_notes=refund_notes,
	)


@frappe.whitelist()
def get_active_reservation_for_vehicle(vehicle_name: str):
	service = VehicleReservationService()
	return service.get_active_reservation_for_vehicle(vehicle_name)


def verify_vehicle_reservation_service():
	service = VehicleReservationService()
	vehicle = None
	item_name = None
	stock_entry_name = None
	serial_no = None
	reservation_name = None
	customer_name = None
	item_existed_before = False
	serial_existed_before = False
	customer_existed_before = False
	verification = {"cleaned_up": False}

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": "VERIFY-RESERVE",
				"vin": f"VERIFY-RESERVE-{frappe.generate_hash(length=10)}",
				"purchase_price": 300000,
			}
		).insert()
		stock_no = vehicle.stock_no
		item_existed_before = bool(frappe.db.exists("Item", stock_no))
		serial_existed_before = bool(frappe.db.exists("Serial No", vehicle.vin))
		customer_existed_before = bool(frappe.db.get_value("Customer", {"customer_name": "王小明"}, "name"))

		intake_result = VehicleIntakeService().complete_intake(vehicle.name)
		item_name = intake_result.get("item")
		stock_entry_name = intake_result.get("stock_entry")
		serial_no = intake_result.get("serial_no")

		VehicleListingService().list_vehicle(vehicle.name)
		vehicle.reload()
		if vehicle.status != "上架中":
			frappe.throw("Vehicle Reservation Service verification requires status 上架中 before reservation.")

		before_counts = _reservation_verification_doc_counts()
		result = service.create_reservation(
			vehicle_name=vehicle.name,
			customer_name="王小明",
			customer_phone="0912345678",
			sold_price=60000,
			deposit_amount=10000,
			payment_method="現金",
			deposit_date=nowdate(),
			payment_reference="VERIFY",
		)
		reservation_name = result.get("reservation")
		customer_name = result.get("customer")
		vehicle.reload()
		after_reservation_counts = _reservation_verification_doc_counts()

		if vehicle.status != "保留中":
			frappe.throw("Vehicle Reservation Service verification did not move vehicle to 保留中.")
		if after_reservation_counts["Journal Entry"] != before_counts["Journal Entry"]:
			frappe.throw("Reservation must not create Journal Entry before accounting confirm.")
		for doctype in ("Payment Entry", "Sales Invoice", "Delivery Note", "Stock Entry"):
			if after_reservation_counts[doctype] != before_counts[doctype]:
				frappe.throw(f"Reservation must not create {doctype}.")

		cancel_result = service.cancel_reservation(reservation_name, "VERIFY CANCEL")
		vehicle.reload()
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		if vehicle.status != "上架中" or reservation.status != "已取消":
			frappe.throw("Cancel reservation did not restore vehicle to 上架中 and mark reservation 已取消.")

		verification = {
			"vehicle_name": vehicle.name,
			"stock_no": stock_no,
			"reservation": reservation_name,
			"customer": customer_name,
			"reservation_status": reservation.status,
			"vehicle_status": vehicle.status,
			"money_flow": result.get("money_flow"),
			"voucher_draft": result.get("voucher_draft"),
			"cancel_message": cancel_result.get("message"),
			"journal_entry_count_unchanged": after_reservation_counts["Journal Entry"] == before_counts["Journal Entry"],
			"payment_entry_count_unchanged": after_reservation_counts["Payment Entry"] == before_counts["Payment Entry"],
			"sales_invoice_count_unchanged": after_reservation_counts["Sales Invoice"] == before_counts["Sales Invoice"],
			"delivery_note_count_unchanged": after_reservation_counts["Delivery Note"] == before_counts["Delivery Note"],
			"stock_entry_count_unchanged_after_reservation": after_reservation_counts["Stock Entry"] == before_counts["Stock Entry"],
			"cleaned_up": False,
		}
	finally:
		try:
			if reservation_name and frappe.db.exists("Used Car Reservation", reservation_name):
				frappe.delete_doc("Used Car Reservation", reservation_name, force=True)
			if stock_entry_name and frappe.db.exists("Stock Entry", stock_entry_name):
				stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
				if stock_entry.docstatus == 1:
					stock_entry.cancel()
				elif stock_entry.docstatus == 0:
					frappe.delete_doc("Stock Entry", stock_entry_name, force=True)
			if vehicle and frappe.db.exists("Used Car Vehicle", vehicle.name):
				frappe.db.set_value("Used Car Vehicle", vehicle.name, {"serial_no": None, "stock_entry": None, "item": None})
				frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
			if serial_no and not serial_existed_before and frappe.db.exists("Serial No", serial_no):
				try:
					frappe.delete_doc("Serial No", serial_no, force=True)
				except Exception:
					verification["serial_no_cleanup_skipped"] = True
			if item_name and not item_existed_before and frappe.db.exists("Item", item_name):
				try:
					frappe.delete_doc("Item", item_name, force=True)
				except Exception:
					verification["item_cleanup_skipped"] = True
			if customer_name and not customer_existed_before and frappe.db.exists("Customer", customer_name):
				try:
					frappe.delete_doc("Customer", customer_name, force=True)
				except Exception:
					verification["customer_cleanup_skipped"] = True
			frappe.db.commit()
			verification["cleaned_up"] = True
		except Exception as exc:
			frappe.db.rollback()
			frappe.throw(f"Vehicle Reservation verification cleanup failed: {exc}")

	return verification


def _reservation_verification_doc_counts():
	counts = {doctype: frappe.db.count(doctype) for doctype in RESTRICTED_ACCOUNTING_DOCTYPES}
	counts["Used Car Reservation"] = frappe.db.count("Used Car Reservation")
	return counts
