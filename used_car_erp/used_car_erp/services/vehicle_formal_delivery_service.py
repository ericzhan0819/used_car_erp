import frappe
from frappe.utils import flt, now_datetime

from used_car_erp.used_car_erp.services.vehicle_final_check_service import (
	RESTRICTED_FINAL_CHECK_DOCTYPES,
	get_sold_vehicle_final_check,
)
from used_car_erp.used_car_erp.services.vehicle_profit_tax_estimate_service import (
	get_vehicle_profit_tax_estimate,
)


AMOUNT_TOLERANCE = 1
READY_LABEL = "可進入 Sales Invoice 正式提交階段"
BLOCKED_LABEL = "尚不可正式提交"
ALLOWED_FORMAL_DELIVERY_STATUSES = {None, "", "銷售發票草稿"}
ALLOWED_TAX_REVIEW_STATUSES = {"已初步判斷", "已確認", "已調整", "已鎖定"}
RESTRICTED_FORMAL_DELIVERY_DOCTYPES = (*RESTRICTED_FINAL_CHECK_DOCTYPES,)
PHASE_3C_FORBIDDEN_DOCTYPES = ("Payment Entry", "Delivery Note", "Stock Entry", "Tax Summary")
SUBMITTED_FORMAL_DELIVERY_STATUS = "銷售發票已提交"
ADVANCE_SETTLEMENT_DRAFT_STATUS = "預收款沖轉草稿"
SUBMIT_ALLOWED_ROLES = {"System Manager", "Accounts Manager", "Accounts User"}
SETTLEMENT_DRAFT_ALLOWED_ROLES = {"System Manager", "Accounts Manager", "Accounts User"}
SETTLEMENT_BLOCKED_MESSAGE = "預收款沖轉傳票草稿建立前檢查未通過。"
SETTLEMENT_LINK_BLOCKED_REASON = "訂金或尾款入帳連結尚未完整，無法建立預收款沖轉草稿。"


def preflight_formal_delivery_submit(vehicle_name: str) -> dict:
	blocked_reasons = []
	checks = []
	sales_invoice_summary = None
	tax_estimate_summary = {}

	final_check = get_sold_vehicle_final_check(vehicle_name)
	checks.append(_build_final_check_gate(final_check, blocked_reasons))

	if final_check.get("status") != "ready":
		return _result(vehicle_name, blocked_reasons, checks, sales_invoice_summary, tax_estimate_summary)

	vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
	vehicle_check = _build_vehicle_gate(vehicle, blocked_reasons)
	checks.append(vehicle_check)

	invoice = None
	if vehicle.sales_invoice and frappe.db.exists("Sales Invoice", vehicle.sales_invoice):
		invoice = frappe.get_doc("Sales Invoice", vehicle.sales_invoice)
		sales_invoice_summary = _build_sales_invoice_summary(invoice)

	checks.append(_build_sales_invoice_gate(vehicle, invoice, blocked_reasons))
	checks.append(_build_amount_gate(vehicle, invoice, blocked_reasons))
	checks.append(_build_tax_metadata_gate(vehicle, blocked_reasons))

	tax_estimate = get_vehicle_profit_tax_estimate(vehicle.name)
	vehicle.reload()
	tax_estimate_summary = _build_tax_estimate_summary(vehicle, tax_estimate)
	checks.append(_build_profit_tax_estimate_gate(vehicle, tax_estimate, blocked_reasons))
	checks.append(_build_cost_summary_gate(vehicle, tax_estimate, blocked_reasons))

	return _result(vehicle.name, blocked_reasons, checks, sales_invoice_summary, tax_estimate_summary)


@frappe.whitelist()
def preflight_formal_delivery_submit_for_vehicle(vehicle_name):
	return preflight_formal_delivery_submit(vehicle_name)


def submit_formal_delivery_sales_invoice(vehicle_name: str, note: str | None = None) -> dict:
	_permission_blocked = _require_formal_delivery_submit_permission()
	if _permission_blocked:
		return _blocked_submit_result(vehicle_name, [_permission_blocked])

	preflight = preflight_formal_delivery_submit(vehicle_name)
	if not _preflight_allows_submit(preflight):
		blocked_reasons = preflight.get("blocked_reasons") or ["Sales Invoice 正式提交前檢查未通過，請先處理待處理項目。"]
		return _blocked_submit_result(vehicle_name, blocked_reasons, preflight=preflight)

	vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
	invoice = frappe.get_doc("Sales Invoice", vehicle.sales_invoice) if vehicle.sales_invoice else None
	blocked_reasons = _validate_sales_invoice_submit_runtime(vehicle, invoice)
	if blocked_reasons:
		return _blocked_submit_result(vehicle.name, blocked_reasons, vehicle=vehicle, invoice=invoice, preflight=preflight)

	before_formal_delivery_status = vehicle.formal_delivery_status
	invoice.submit()

	# Phase 3B 僅允許留下提交節點，避免提早標記正式交車完成或沖轉預收款。
	vehicle.db_set("formal_delivery_status", SUBMITTED_FORMAL_DELIVERY_STATUS, update_modified=True)
	vehicle.db_set("formal_delivery_posting_date", invoice.posting_date, update_modified=True)
	if note:
		vehicle.db_set("formal_delivery_note", note, update_modified=True)

	_add_formal_delivery_comment(
		vehicle.name,
		f"Sales Invoice {invoice.name} 已提交；Phase 3B 僅完成 update_stock 出庫，預收款沖轉仍待後續處理。",
	)

	return {
		"vehicle": vehicle.name,
		"status": "submitted",
		"message": "Sales Invoice 已正式提交並依 update_stock 出庫。預收款沖轉仍待後續處理。",
		"sales_invoice": invoice.name,
		"sales_invoice_docstatus": invoice.docstatus,
		"formal_delivery_status": SUBMITTED_FORMAL_DELIVERY_STATUS,
		"before_formal_delivery_status": before_formal_delivery_status,
		"next_step": "建立預收款沖轉 Journal Entry 草稿",
	}


@frappe.whitelist()
def submit_formal_delivery_sales_invoice_for_vehicle(vehicle_name, note=None):
	return submit_formal_delivery_sales_invoice(vehicle_name, note=note)


def create_advance_settlement_journal_entry_draft(vehicle_name: str, note: str | None = None) -> dict:
	permission_blocked = _require_advance_settlement_draft_permission()
	if permission_blocked:
		return _blocked_settlement_result(vehicle_name, [permission_blocked])

	vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
	sales_invoice = (
		frappe.get_doc("Sales Invoice", vehicle.sales_invoice)
		if vehicle.sales_invoice and frappe.db.exists("Sales Invoice", vehicle.sales_invoice)
		else None
	)
	blocked_reasons = _validate_advance_settlement_preconditions(vehicle, sales_invoice)
	deposit_journal_entry = None
	final_journal_entry = None

	if not blocked_reasons:
		deposit_journal_entry, final_journal_entry = _load_submitted_advance_journal_entries(vehicle, blocked_reasons)

	settlement_amount = 0
	if not blocked_reasons:
		settlement_amount = _resolve_settlement_amount(sales_invoice, vehicle, blocked_reasons)

	advance_liability_account = None
	if not blocked_reasons:
		advance_liability_account = _resolve_common_advance_liability_account(deposit_journal_entry, final_journal_entry, blocked_reasons)

	receivable_account = sales_invoice.debit_to if sales_invoice else None
	if not blocked_reasons and not receivable_account:
		blocked_reasons.append("Sales Invoice 應收帳款科目缺失，請先人工確認。")

	if blocked_reasons:
		_add_formal_delivery_comment(vehicle.name, f"{SETTLEMENT_BLOCKED_MESSAGE} {' '.join(blocked_reasons)}")
		return _blocked_settlement_result(vehicle.name, blocked_reasons)

	journal_entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": sales_invoice.company,
			"posting_date": sales_invoice.posting_date,
			"user_remark": _build_advance_settlement_user_remark(vehicle, sales_invoice, settlement_amount, note),
			"accounts": [
				{
					"account": advance_liability_account,
					"debit_in_account_currency": settlement_amount,
					"credit_in_account_currency": 0,
				},
				{
					"account": receivable_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": settlement_amount,
				},
			],
		}
	).insert()

	if journal_entry.docstatus != 0:
		frappe.throw("預收款沖轉 Journal Entry 必須保持草稿狀態。")

	# Phase 3C 只允許連結草稿與狀態前進，不提交傳票、不完成交車，避免會計與庫存 side effect 提早發生。
	vehicle.db_set("advance_settlement_journal_entry", journal_entry.name, update_modified=True)
	vehicle.db_set("formal_delivery_status", ADVANCE_SETTLEMENT_DRAFT_STATUS, update_modified=True)
	if note:
		vehicle.db_set("formal_delivery_note", note, update_modified=True)

	_add_formal_delivery_comment(
		vehicle.name,
		f"預收款沖轉 Journal Entry 草稿 {journal_entry.name} 已建立；Phase 3C 不提交 Journal Entry，仍需會計人工確認。",
	)

	return {
		"vehicle": vehicle.name,
		"status": "draft_created",
		"message": "預收款沖轉 Journal Entry 草稿已建立，仍需會計人工確認與提交。",
		"sales_invoice": sales_invoice.name,
		"journal_entry": journal_entry.name,
		"journal_entry_docstatus": journal_entry.docstatus,
		"settlement_amount": settlement_amount,
		"advance_liability_account": advance_liability_account,
		"receivable_account": receivable_account,
		"formal_delivery_status": ADVANCE_SETTLEMENT_DRAFT_STATUS,
		"next_step": "會計確認並提交預收款沖轉 Journal Entry",
	}


@frappe.whitelist()
def create_advance_settlement_journal_entry_draft_for_vehicle(vehicle_name, note=None):
	return create_advance_settlement_journal_entry_draft(vehicle_name, note=note)


def verify_formal_delivery_submit_preflight_service():
	vehicle_name = None
	before_counts = _restricted_doc_counts()

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"VERIFY-FORMAL-PREFLIGHT-{frappe.generate_hash(length=4)}",
				"vin": f"VERIFY-FORMAL-PREFLIGHT-{frappe.generate_hash(length=10)}",
				"status": "已售出",
				"completed_reservation": "VERIFY-RESERVATION",
				"completed_at": now_datetime(),
				"deposit_money_flow": "VERIFY-DEPOSIT-FLOW",
				"deposit_voucher_draft": "VERIFY-DEPOSIT-DRAFT",
				"deposit_journal_entry": "VERIFY-DEPOSIT-JE",
				"final_money_flow": "VERIFY-FINAL-FLOW",
				"final_voucher_draft": "VERIFY-FINAL-DRAFT",
				"final_journal_entry": "VERIFY-FINAL-JE",
				"item": "VERIFY-ITEM",
				"serial_no": "VERIFY-SERIAL",
				"stock_warehouse": "VERIFY-WAREHOUSE",
				"purchase_price": 500000,
				"sold_price": 600000,
				"vehicle_tax_mode": "15-1 特殊扣抵",
				"tax_review_status": "已確認",
			}
		).insert(ignore_links=True)
		vehicle_name = vehicle.name

		result = preflight_formal_delivery_submit(vehicle.name)
		after_counts = _restricted_doc_counts()

		if result["status"] != "blocked":
			frappe.throw("Formal delivery preflight verification should be blocked without Sales Invoice draft.")
		for doctype in RESTRICTED_FORMAL_DELIVERY_DOCTYPES:
			if after_counts[doctype] != before_counts[doctype]:
				frappe.throw(f"Formal delivery preflight must not create {doctype}.")

		return {**result, "cleaned_up": True}
	finally:
		if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
			frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True, ignore_permissions=True)
		frappe.db.commit()


def verify_formal_delivery_sales_invoice_submit_service():
	vehicle_name = None
	before_counts = _restricted_doc_counts()

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"VERIFY-FORMAL-SUBMIT-{frappe.generate_hash(length=4)}",
				"vin": f"VERIFY-FORMAL-SUBMIT-{frappe.generate_hash(length=10)}",
				"status": "已售出",
				"completed_reservation": "VERIFY-RESERVATION",
				"completed_at": now_datetime(),
				"deposit_money_flow": "VERIFY-DEPOSIT-FLOW",
				"deposit_voucher_draft": "VERIFY-DEPOSIT-DRAFT",
				"deposit_journal_entry": "VERIFY-DEPOSIT-JE",
				"final_money_flow": "VERIFY-FINAL-FLOW",
				"final_voucher_draft": "VERIFY-FINAL-DRAFT",
				"final_journal_entry": "VERIFY-FINAL-JE",
				"item": "VERIFY-ITEM",
				"serial_no": "VERIFY-SERIAL",
				"stock_warehouse": "VERIFY-WAREHOUSE",
				"purchase_price": 500000,
				"sold_price": 600000,
				"vehicle_tax_mode": "15-1 特殊扣抵",
				"tax_review_status": "已確認",
			}
		).insert(ignore_links=True)
		vehicle_name = vehicle.name

		result = submit_formal_delivery_sales_invoice(vehicle.name)
		if result["status"] != "blocked":
			frappe.throw("Formal delivery submit verification should be blocked without Sales Invoice draft.")
		if frappe.db.get_value("Used Car Vehicle", vehicle.name, "formal_delivery_status") != vehicle.formal_delivery_status:
			frappe.throw("Blocked submit must not change vehicle formal delivery status.")
		for doctype, before_count in before_counts.items():
			if _restricted_doc_counts()[doctype] != before_count:
				frappe.throw(f"Formal delivery submit blocked case must not create {doctype}.")

		return {**result, "cleaned_up": True}
	finally:
		if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
			frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True, ignore_permissions=True)
		frappe.db.commit()


def verify_advance_settlement_journal_entry_draft_service():
	vehicle_name = None
	before_counts = _settlement_restricted_doc_counts()

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": f"VERIFY-SETTLEMENT-{frappe.generate_hash(length=4)}",
				"vin": f"VERIFY-SETTLEMENT-{frappe.generate_hash(length=10)}",
				"status": "已售出",
				"formal_delivery_status": "未處理",
				"completed_reservation": "VERIFY-RESERVATION",
				"completed_at": now_datetime(),
				"purchase_price": 500000,
				"sold_price": 600000,
			}
		).insert(ignore_links=True)
		vehicle_name = vehicle.name

		result = create_advance_settlement_journal_entry_draft(vehicle.name)
		after_counts = _settlement_restricted_doc_counts()

		if result["status"] != "blocked":
			frappe.throw("Advance settlement draft verification should be blocked without Phase 3C prerequisites.")
		if after_counts["Journal Entry"] != before_counts["Journal Entry"]:
			frappe.throw("Blocked advance settlement verification must not create Journal Entry.")
		for doctype in ("Payment Entry", "Delivery Note", "Stock Entry", "Tax Summary"):
			if after_counts[doctype] != before_counts[doctype]:
				frappe.throw(f"Blocked advance settlement verification must not create {doctype}.")

		return {**result, "cleaned_up": True}
	finally:
		if vehicle_name and frappe.db.exists("Used Car Vehicle", vehicle_name):
			frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True, ignore_permissions=True)
		frappe.db.commit()


def _build_final_check_gate(final_check, blocked_reasons):
	status = final_check.get("status")
	status_label = final_check.get("status_label") or status
	if status == "ready":
		return _check("final_check", "交車前最終檢查", "ok", f"交車前最終檢查已通過，狀態：{status_label}。")
	if status == "warning":
		message = f"交車前最終檢查仍有待確認項目，狀態：{status_label}。"
	else:
		message = f"交車前最終檢查尚未通過，狀態：{status_label}。"
	blocked_reasons.append(message)
	return _check("final_check", "交車前最終檢查", "blocked", message)


def _require_formal_delivery_submit_permission():
	if frappe.session.user == "Administrator":
		return None
	user_roles = set(frappe.get_roles(frappe.session.user))
	if user_roles.intersection(SUBMIT_ALLOWED_ROLES):
		return None
	# 尚未導入 formal_delivery.submit_sales_invoice 權限鍵前，先用保守會計/系統角色避免 Sales 角色誤觸正式入帳 mutation。
	return "只有 System Manager、Accounts Manager 或 Accounts User 可提交正式 Sales Invoice。"


def _require_advance_settlement_draft_permission():
	if frappe.session.user == "Administrator":
		return None
	user_roles = set(frappe.get_roles(frappe.session.user))
	if user_roles.intersection(SETTLEMENT_DRAFT_ALLOWED_ROLES):
		return None
	# 未來應改用 formal_delivery.create_settlement_draft 權限鍵；目前先用會計層級角色避免銷售人員建立會計沖轉草稿。
	return "只有 Administrator、System Manager、Accounts Manager 或 Accounts User 可建立預收款沖轉草稿。"


def _validate_advance_settlement_preconditions(vehicle, sales_invoice):
	reasons = []
	if vehicle.status != "已售出":
		reasons.append("車輛狀態必須為已售出。")
	if vehicle.formal_delivery_status != SUBMITTED_FORMAL_DELIVERY_STATUS:
		reasons.append("正式交車入帳狀態必須為銷售發票已提交。")
	if not vehicle.sales_invoice:
		reasons.append("車輛尚未連結 Sales Invoice。")
	if not sales_invoice:
		reasons.append("Sales Invoice 不存在。")
	else:
		if sales_invoice.docstatus != 1:
			reasons.append("Sales Invoice 尚未提交，無法建立預收款沖轉草稿。")
		if flt(sales_invoice.grand_total) <= 0:
			reasons.append("Sales Invoice 總金額必須大於 0。")
		if not sales_invoice.debit_to:
			reasons.append("Sales Invoice 應收帳款科目缺失，請先人工確認。")
	if vehicle.advance_settlement_journal_entry:
		reasons.append("預收款沖轉傳票草稿已存在，請先人工確認既有草稿。")
	return reasons


def _load_submitted_advance_journal_entries(vehicle, blocked_reasons):
	required_links = [
		"deposit_money_flow",
		"deposit_voucher_draft",
		"deposit_journal_entry",
		"final_money_flow",
		"final_voucher_draft",
		"final_journal_entry",
	]
	if any(not vehicle.get(fieldname) for fieldname in required_links):
		blocked_reasons.append(SETTLEMENT_LINK_BLOCKED_REASON)
		return None, None

	journal_entries = []
	for fieldname in ("deposit_journal_entry", "final_journal_entry"):
		journal_entry_name = vehicle.get(fieldname)
		if not frappe.db.exists("Journal Entry", journal_entry_name):
			blocked_reasons.append(SETTLEMENT_LINK_BLOCKED_REASON)
			return None, None
		journal_entry = frappe.get_doc("Journal Entry", journal_entry_name)
		if journal_entry.docstatus != 1:
			blocked_reasons.append(SETTLEMENT_LINK_BLOCKED_REASON)
			return None, None
		journal_entries.append(journal_entry)

	return journal_entries[0], journal_entries[1]


def _resolve_settlement_amount(sales_invoice, vehicle, blocked_reasons):
	if flt(sales_invoice.outstanding_amount) <= 0:
		blocked_reasons.append("Sales Invoice 應收餘額不足，請先人工確認是否已被沖銷或付款。")
		return 0

	settlement_amount = flt(sales_invoice.outstanding_amount or sales_invoice.grand_total)
	if settlement_amount <= 0 or settlement_amount > flt(sales_invoice.grand_total):
		blocked_reasons.append("Sales Invoice 應收餘額不足，請先人工確認是否已被沖銷或付款。")
		return 0

	total_advance_received = _resolve_total_advance_received(vehicle)
	if total_advance_received is not None and abs(total_advance_received - flt(sales_invoice.grand_total)) > AMOUNT_TOLERANCE:
		blocked_reasons.append("預收款金額與 Sales Invoice 金額不一致，請先人工確認是否有溢收或退款。")
		return 0

	return settlement_amount


def _resolve_total_advance_received(vehicle):
	amounts = []
	for fieldname in ("deposit_money_flow", "final_money_flow"):
		money_flow_name = vehicle.get(fieldname)
		if not money_flow_name or not frappe.db.exists("Used Car Money Flow", money_flow_name):
			return None
		amount = frappe.db.get_value("Used Car Money Flow", money_flow_name, "amount")
		if amount is None:
			return None
		amounts.append(flt(amount))
	return sum(amounts)


def _resolve_common_advance_liability_account(deposit_journal_entry, final_journal_entry, blocked_reasons):
	deposit_accounts = _resolve_liability_candidate_accounts(deposit_journal_entry)
	final_accounts = _resolve_liability_candidate_accounts(final_journal_entry)
	if not deposit_accounts or not final_accounts:
		blocked_reasons.append("無法從訂金 / 尾款正式會計傳票解析預收款科目，請先人工確認。")
		return None

	common_accounts = deposit_accounts.intersection(final_accounts)
	all_accounts = deposit_accounts.union(final_accounts)
	if len(all_accounts) > 1 or len(common_accounts) != 1:
		blocked_reasons.append("訂金與尾款使用不同預收款科目，請先人工確認沖轉科目。")
		return None
	return next(iter(common_accounts))


def _resolve_liability_candidate_accounts(journal_entry):
	candidates = set()
	for row in journal_entry.accounts:
		if flt(row.credit_in_account_currency or row.credit) <= 0 or not row.account:
			continue
		account_type, root_type = _get_account_values(row.account)
		if account_type in {"Bank", "Cash", "Receivable"}:
			continue
		if root_type == "Asset":
			continue
		if root_type == "Liability" or account_type in {"Payable", "Temporary"}:
			candidates.add(row.account)
	return candidates


def _build_advance_settlement_user_remark(vehicle, sales_invoice, settlement_amount, note):
	parts = [
		"Phase 3C 預收款沖轉 Journal Entry 草稿。",
		f"車輛：{vehicle.name}。",
		f"Sales Invoice：{sales_invoice.name}。",
		f"沖轉金額：{settlement_amount}。",
		"沖轉金額依 Sales Invoice outstanding_amount 建立，仍需會計人工確認。",
	]
	if note:
		parts.append(f"備註：{note}")
	return " ".join(parts)


def _get_account_values(account_name):
	return frappe.db.get_value("Account", account_name, ["account_type", "root_type"]) or (None, None)


def _blocked_settlement_result(vehicle_name, blocked_reasons):
	return {
		"vehicle": vehicle_name,
		"status": "blocked",
		"message": SETTLEMENT_BLOCKED_MESSAGE,
		"blocked_reasons": blocked_reasons,
	}


def _preflight_allows_submit(preflight):
	return preflight.get("ready") is True and preflight.get("status") == "ready" and not preflight.get("blocked_reasons")


def _validate_sales_invoice_submit_runtime(vehicle, invoice):
	reasons = []
	if vehicle.status != "已售出":
		reasons.append("車輛狀態必須為已售出。")
	if not vehicle.sales_invoice:
		reasons.append("車輛尚未連結 Sales Invoice 草稿。")
	if vehicle.formal_delivery_status not in ALLOWED_FORMAL_DELIVERY_STATUSES:
		reasons.append("此車輛已進入正式交車後續狀態，不可重複提交 Sales Invoice。")
	if not invoice:
		reasons.append("Sales Invoice 草稿不存在。")
		return reasons

	items = invoice.items or []
	first_item = items[0] if items else None
	if invoice.docstatus != 0:
		reasons.append("Sales Invoice 已不是草稿，請人工確認。")
	if invoice.update_stock != 1:
		reasons.append("Sales Invoice 必須啟用 Update Stock。")
	if len(items) != 1:
		reasons.append("Sales Invoice 必須只有一筆車輛 item。")
	if first_item:
		if not first_item.item_code:
			reasons.append("Sales Invoice item_code 尚未完整。")
		if flt(first_item.qty) != 1:
			reasons.append("Sales Invoice 車輛數量必須為 1。")
		if not first_item.serial_no or not first_item.warehouse or not first_item.income_account:
			reasons.append("Sales Invoice 車輛 item 的 Serial No、Warehouse 或 Income Account 尚未完整。")
	if flt(vehicle.sold_price) <= 0 or abs(flt(invoice.grand_total) - flt(vehicle.sold_price)) > AMOUNT_TOLERANCE:
		reasons.append("Sales Invoice 金額與車輛成交價不一致，請先人工確認草稿。")

	return reasons


def _blocked_submit_result(vehicle_name, blocked_reasons, vehicle=None, invoice=None, preflight=None):
	message = "Sales Invoice 正式提交前檢查未通過。"
	if vehicle:
		_add_formal_delivery_comment(vehicle.name, f"{message} {' '.join(blocked_reasons)}")
	return {
		"vehicle": vehicle.name if vehicle else vehicle_name,
		"status": "blocked",
		"message": message,
		"blocked_reasons": blocked_reasons,
		"sales_invoice": invoice.name if invoice else None,
		"sales_invoice_docstatus": invoice.docstatus if invoice else None,
		"preflight_status": preflight.get("status") if preflight else None,
	}


def _add_formal_delivery_comment(vehicle_name, text):
	try:
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		vehicle.add_comment("Comment", text)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Formal Delivery Phase 3B audit comment failed")


def _build_vehicle_gate(vehicle, blocked_reasons):
	reasons = []
	if vehicle.status != "已售出":
		reasons.append("車輛狀態必須為已售出。")
	if not vehicle.sales_invoice:
		reasons.append("車輛尚未連結 Sales Invoice 草稿。")
	if not vehicle.item or not vehicle.serial_no or not vehicle.stock_warehouse:
		reasons.append("ERPNext Item、Serial No 或 Warehouse 尚未完整。")
	if vehicle.formal_delivery_status not in ALLOWED_FORMAL_DELIVERY_STATUSES:
		reasons.append("此車輛已進入正式交車後續狀態，不可重複進行提交前檢查。")

	if reasons:
		blocked_reasons.extend(reasons)
		return _check("vehicle_status", "車輛狀態", "blocked", " ".join(reasons))
	return _check("vehicle_status", "車輛狀態", "ok", "車輛已售出，且 ERPNext 庫存連結與正式交車狀態可進入提交前檢查。")


def _build_sales_invoice_gate(vehicle, invoice, blocked_reasons):
	reasons = []
	items = invoice.items if invoice else []
	first_item = items[0] if items else None

	if not vehicle.sales_invoice or not invoice:
		reasons.append("Sales Invoice 草稿尚未建立。")
	else:
		if invoice.docstatus != 0:
			reasons.append("Sales Invoice 已不是草稿，請人工確認。")
		if not invoice.customer or not invoice.company or not invoice.posting_date:
			reasons.append("Sales Invoice 客戶、公司或入帳日期尚未完整。")
		if flt(invoice.grand_total) <= 0:
			reasons.append("Sales Invoice 總金額必須大於 0。")
		if invoice.update_stock != 1:
			reasons.append("Sales Invoice 必須啟用 Update Stock。")
		if not items:
			reasons.append("Sales Invoice 必須至少有一筆 item。")
		if len(items) > 1:
			reasons.append("Sales Invoice 應只有一筆車輛 item；目前有多筆 item，請人工確認。")
		if first_item:
			if not first_item.item_code or flt(first_item.qty) != 1 or flt(first_item.rate) <= 0 or flt(first_item.amount) <= 0:
				reasons.append("Sales Invoice 車輛 item、數量、單價或金額尚未完整。")
			if not first_item.serial_no or not first_item.warehouse or not first_item.income_account:
				reasons.append("Sales Invoice 車輛 item 的 Serial No、Warehouse 或 Income Account 尚未完整。")

	if reasons:
		blocked_reasons.extend(reasons)
		return _check("sales_invoice_draft", "Sales Invoice 草稿", "blocked", " ".join(reasons))
	return _check("sales_invoice_draft", "Sales Invoice 草稿", "ok", "Sales Invoice 草稿欄位已符合提交前檢查條件。")


def _build_amount_gate(vehicle, invoice, blocked_reasons):
	if not invoice or not invoice.items:
		message = "Sales Invoice 金額資料尚未完整，無法比對車輛成交價。"
		blocked_reasons.append(message)
		return _check("amount_consistency", "金額一致性", "blocked", message)

	sold_price = flt(vehicle.sold_price)
	item_amount = flt(invoice.items[0].amount)
	if (
		sold_price <= 0
		or abs(flt(invoice.grand_total) - sold_price) > AMOUNT_TOLERANCE
		or abs(item_amount - sold_price) > AMOUNT_TOLERANCE
	):
		message = "Sales Invoice 金額與車輛成交價不一致，請先人工確認草稿。"
		blocked_reasons.append(message)
		return _check("amount_consistency", "金額一致性", "blocked", message)
	return _check("amount_consistency", "金額一致性", "ok", "Sales Invoice 金額與車輛成交價一致。")


def _build_tax_metadata_gate(vehicle, blocked_reasons):
	# Phase 3A 先允許初步判斷；正式上線提交時可考慮只允許「已確認 / 已鎖定」。
	if vehicle.vehicle_tax_mode == "待確認" or vehicle.tax_review_status not in ALLOWED_TAX_REVIEW_STATUSES:
		message = "稅務資料尚未達到正式提交前檢查條件；請先確認稅務模式與稅務確認狀態。"
		blocked_reasons.append(message)
		return _check("tax_metadata", "稅務資料", "blocked", message)
	return _check("tax_metadata", "稅務資料", "ok", "稅務模式與稅務確認狀態已符合 Phase 3A 條件。")


def _build_profit_tax_estimate_gate(vehicle, tax_estimate, blocked_reasons):
	status = tax_estimate.get("tax_estimate_status")
	blocked = (
		status in {"資料不足", "需確認"}
		or flt(tax_estimate.get("estimated_output_vat")) < 0
		or flt(tax_estimate.get("estimated_vat_payable")) < 0
	)
	if vehicle.vehicle_tax_mode == "15-1 特殊扣抵":
		blocked = blocked or flt(tax_estimate.get("estimated_15_1_input_credit")) > flt(tax_estimate.get("estimated_output_vat"))

	if blocked:
		message = "損益與營業稅估算尚未達到正式提交前檢查條件。"
		blocked_reasons.append(message)
		return _check("profit_tax_estimate", "損益與營業稅估算", "blocked", message)
	return _check("profit_tax_estimate", "損益與營業稅估算", "ok", "損益與營業稅估算已符合提交前檢查條件。")


def _build_cost_summary_gate(vehicle, tax_estimate, blocked_reasons):
	purchase_price = flt(tax_estimate.get("purchase_price") or vehicle.purchase_price)
	total_cost = flt(tax_estimate.get("total_cost") or vehicle.total_cost)
	sold_price = flt(vehicle.sold_price)
	gross_margin = tax_estimate.get("gross_margin") if tax_estimate.get("gross_margin") is not None else vehicle.gross_margin

	if purchase_price <= 0 or total_cost < purchase_price or sold_price <= 0 or gross_margin is None:
		message = "成本摘要尚未達到正式提交前檢查條件。"
		blocked_reasons.append(message)
		return _check("cost_summary", "成本摘要", "blocked", message)
	return _check("cost_summary", "成本摘要", "ok", "買入金額、累計成本、成交價與毛利估算已可供提交前檢查。")


def _build_sales_invoice_summary(invoice):
	first_item = invoice.items[0] if invoice.items else None
	return {
		"name": invoice.name,
		"docstatus": invoice.docstatus,
		"customer": invoice.customer,
		"company": invoice.company,
		"posting_date": invoice.posting_date,
		"grand_total": flt(invoice.grand_total),
		"update_stock": invoice.update_stock,
		"item_code": first_item.item_code if first_item else None,
		"serial_no": first_item.serial_no if first_item else None,
		"warehouse": first_item.warehouse if first_item else None,
		"income_account": first_item.income_account if first_item else None,
	}


def _build_tax_estimate_summary(vehicle, tax_estimate):
	return {
		"vehicle_tax_mode": tax_estimate.get("vehicle_tax_mode") or vehicle.vehicle_tax_mode,
		"tax_review_status": tax_estimate.get("tax_review_status") or vehicle.tax_review_status,
		"estimated_output_vat": flt(tax_estimate.get("estimated_output_vat")),
		"estimated_input_credit": flt(tax_estimate.get("estimated_input_credit")),
		"estimated_vat_payable": flt(tax_estimate.get("estimated_vat_payable")),
		"estimated_margin_after_vat": flt(tax_estimate.get("estimated_margin_after_vat")),
	}


def _result(vehicle_name, blocked_reasons, checks, sales_invoice, tax_estimate):
	ready = not blocked_reasons and all(check["state"] == "ok" for check in checks)
	return {
		"vehicle": vehicle_name,
		"ready": ready,
		"status": "ready" if ready else "blocked",
		"status_label": READY_LABEL if ready else BLOCKED_LABEL,
		"blocked_reasons": blocked_reasons,
		"checks": checks,
		"sales_invoice": sales_invoice or {},
		"tax_estimate": tax_estimate or {},
	}


def _check(key, label, state, message):
	return {"key": key, "label": label, "state": state, "message": message}


def _restricted_doc_counts():
	counts = {}
	for doctype in RESTRICTED_FORMAL_DELIVERY_DOCTYPES:
		counts[doctype] = frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
	return counts


def _settlement_restricted_doc_counts():
	counts = {"Journal Entry": frappe.db.count("Journal Entry") if frappe.db.table_exists("Journal Entry") else 0}
	for doctype in PHASE_3C_FORBIDDEN_DOCTYPES:
		counts[doctype] = frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
	return counts
