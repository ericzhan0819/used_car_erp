import frappe
from frappe.utils import flt, now

from used_car_erp.used_car_erp.services.used_car_action_permission_service import assert_can_perform_used_car_action


class VehicleVoucherService:
	def create_deposit_voucher_draft(self, money_flow_name: str):
		money_flow = frappe.get_doc("Used Car Money Flow", money_flow_name)
		self._validate_money_flow_for_draft(money_flow, "訂金收款")
		debit_account, credit_account = self._resolve_deposit_accounts()
		self._validate_same_company_accounts([debit_account, credit_account])

		draft = frappe.get_doc(
			{
				"doctype": "Used Car Voucher Draft",
				"status": "待審核",
				"posting_date": money_flow.payment_date,
				"money_flow": money_flow.name,
				"vehicle": money_flow.vehicle,
				"reservation": money_flow.reservation,
				"customer": money_flow.customer,
				"memo": f"訂金收款：{money_flow.stock_no or money_flow.vehicle} / {money_flow.customer_name or ''}",
				"review_note": "系統自動建議科目，請會計確認。",
				"lines": [
					{
						"account": debit_account,
						"debit": money_flow.amount,
						"credit": 0,
						"note": "訂金收款科目",
					},
					{
						"account": credit_account,
						"debit": 0,
						"credit": money_flow.amount,
						"note": "訂金預收款 / 暫收款",
					},
				],
			}
		).insert()

		frappe.db.set_value("Used Car Money Flow", money_flow.name, "voucher_draft", draft.name)
		if money_flow.reservation and frappe.get_meta("Used Car Reservation").has_field("voucher_draft"):
			frappe.db.set_value("Used Car Reservation", money_flow.reservation, "voucher_draft", draft.name)

		return draft.name

	def create_final_payment_voucher_draft(self, money_flow_name: str):
		money_flow = frappe.get_doc("Used Car Money Flow", money_flow_name)
		self._validate_money_flow_for_draft(money_flow, "尾款收款")
		debit_account, credit_account = self._resolve_deposit_accounts()
		self._validate_same_company_accounts([debit_account, credit_account])

		draft = frappe.get_doc(
			{
				"doctype": "Used Car Voucher Draft",
				"status": "待審核",
				"posting_date": money_flow.payment_date,
				"money_flow": money_flow.name,
				"vehicle": money_flow.vehicle,
				"reservation": money_flow.reservation,
				"customer": money_flow.customer,
				"memo": f"尾款收款：{money_flow.stock_no or money_flow.vehicle} / {money_flow.customer_name or ''}",
				"review_note": "系統自動建議科目，請會計確認。",
				"lines": [
					{
						"account": debit_account,
						"debit": money_flow.amount,
						"credit": 0,
						"note": "尾款收款科目",
					},
					{
						"account": credit_account,
						"debit": 0,
						"credit": money_flow.amount,
						"note": "尾款預收款 / 暫收款",
					},
				],
			}
		).insert()

		frappe.db.set_value("Used Car Money Flow", money_flow.name, "voucher_draft", draft.name)
		if money_flow.reservation and frappe.get_meta("Used Car Reservation").has_field("final_voucher_draft"):
			frappe.db.set_value("Used Car Reservation", money_flow.reservation, "final_voucher_draft", draft.name)

		return draft.name

	def confirm_voucher_draft(self, voucher_draft_name: str, review_note: str | None = None):
		assert_can_perform_used_car_action(
			"used_car_voucher_draft.confirm",
			message="你沒有確認中古車傳票草稿的權限。",
		)
		draft = frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)
		draft.check_permission("write")
		self._validate_draft_ready_for_confirm(draft)
		company = self._validate_draft_accounts(draft)

		try:
			journal_entry = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"voucher_type": "Journal Entry",
					"company": company,
					"posting_date": draft.posting_date,
					"remark": draft.memo,
					"accounts": [
						{
							"account": line.account,
							"debit_in_account_currency": flt(line.debit),
							"credit_in_account_currency": flt(line.credit),
							"user_remark": line.note,
						}
						for line in draft.lines
					],
				}
			).insert()
			journal_entry.submit()

			draft.status = "已入帳"
			draft.journal_entry = journal_entry.name
			draft.reviewed_by = frappe.session.user
			draft.reviewed_at = now()
			draft.review_note = review_note
			draft.save()

			money_flow = frappe.get_doc("Used Car Money Flow", draft.money_flow)
			money_flow.status = "已入帳"
			money_flow.journal_entry = journal_entry.name
			money_flow.save()

			if draft.reservation:
				self._set_reservation_journal_entry(draft.reservation, money_flow.flow_type, journal_entry.name)

			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise

		return {
			"voucher_draft": draft.name,
			"journal_entry": journal_entry.name,
			"status": "已入帳",
			"message": "已確認入帳並建立正式會計傳票。",
		}

	def reject_voucher_draft(self, voucher_draft_name: str, reason: str):
		assert_can_perform_used_car_action(
			"used_car_voucher_draft.reject",
			message="你沒有退回中古車傳票草稿的權限。",
		)
		if not reason:
			frappe.throw("退回原因為必填。")

		draft = frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)
		draft.check_permission("write")
		if draft.status != "待審核":
			frappe.throw("只有待審核傳票草稿可以退回。")

		draft.status = "已退回"
		draft.reviewed_by = frappe.session.user
		draft.reviewed_at = now()
		draft.review_note = reason
		draft.save()
		frappe.db.commit()
		return {"voucher_draft": draft.name, "status": "已退回", "message": "已退回傳票草稿。"}

	def void_voucher_draft(self, voucher_draft_name: str, reason: str):
		assert_can_perform_used_car_action(
			"used_car_voucher_draft.void",
			message="你沒有作廢中古車傳票草稿的權限。",
		)
		if not reason:
			frappe.throw("作廢原因為必填。")

		draft = frappe.get_doc("Used Car Voucher Draft", voucher_draft_name)
		draft.check_permission("write")
		if draft.status not in ("待審核", "已退回"):
			frappe.throw("只有待審核或已退回且尚未入帳的傳票草稿可以作廢。")
		if draft.journal_entry:
			frappe.throw("已建立正式會計傳票的草稿不可作廢；未來需走反向傳票流程。")

		draft.status = "已作廢"
		draft.reviewed_by = frappe.session.user
		draft.reviewed_at = now()
		draft.review_note = reason
		draft.save()

		money_flow = frappe.get_doc("Used Car Money Flow", draft.money_flow)
		money_flow.status = "已作廢"
		money_flow.save()
		frappe.db.commit()
		return {"voucher_draft": draft.name, "status": "已作廢", "message": "已作廢傳票草稿。"}

	def _validate_money_flow_for_draft(self, money_flow, flow_type: str):
		if money_flow.status != "待審核":
			frappe.throw("只有待審核金流紀錄可以建立傳票草稿。")
		if money_flow.flow_type != flow_type:
			frappe.throw(f"本次只支援{flow_type}建立傳票草稿。")
		if flt(money_flow.amount) <= 0:
			frappe.throw("金流金額必須大於 0。")
		if money_flow.voucher_draft or frappe.db.exists("Used Car Voucher Draft", {"money_flow": money_flow.name}):
			frappe.throw("此金流紀錄已建立傳票草稿。")

	def _validate_draft_ready_for_confirm(self, draft):
		if draft.status != "待審核":
			frappe.throw("只有待審核傳票草稿可以確認入帳。")
		if draft.journal_entry:
			frappe.throw("此傳票草稿已建立正式會計傳票。")
		if not draft.lines:
			frappe.throw("傳票草稿至少需要一筆分錄明細。")
		draft.run_method("validate")

	def _validate_draft_accounts(self, draft):
		accounts = [line.account for line in draft.lines]
		self._validate_same_company_accounts(accounts)
		return frappe.db.get_value("Account", accounts[0], "company")

	def _validate_same_company_accounts(self, accounts):
		companies = set()
		for account_name in accounts:
			account = frappe.get_doc("Account", account_name)
			if account.is_group:
				frappe.throw("傳票分錄不可使用群組會計科目。")
			companies.add(account.company)
		if len(companies) != 1:
			frappe.throw("所有會計科目必須屬於同一家公司。")

	def _set_reservation_journal_entry(self, reservation_name: str, flow_type: str, journal_entry_name: str):
		if not frappe.db.exists("Used Car Reservation", reservation_name):
			return
		reservation = frappe.get_doc("Used Car Reservation", reservation_name)
		reservation.flags.ignore_accounting_link_validation = True
		reservation_meta = frappe.get_meta("Used Car Reservation")
		if flow_type == "尾款收款" and reservation_meta.has_field("final_journal_entry"):
			reservation.final_journal_entry = journal_entry_name
		elif reservation_meta.has_field("journal_entry"):
			reservation.journal_entry = journal_entry_name
		reservation.save()

	def _resolve_deposit_accounts(self):
		debit_account = self._first_account({"is_group": 0, "account_type": "Bank"})
		if not debit_account:
			debit_account = self._first_account({"is_group": 0, "account_type": "Cash"})
		if not debit_account:
			frappe.throw("找不到可用的收款科目，請先建立或設定銀行 / 現金科目。")

		credit_account = self._account_name_contains("預收")
		if not credit_account:
			credit_account = self._account_name_contains("暫收")
		if not credit_account:
			credit_account = self._first_account({"is_group": 0, "root_type": "Liability"})
		if not credit_account:
			frappe.throw("找不到可用的預收款 / 暫收款科目，請先建立或設定負債科目。")

		return debit_account, credit_account

	def _account_name_contains(self, keyword: str):
		return frappe.db.get_value(
			"Account",
			{"is_group": 0, "name": ["like", f"%{keyword}%"]},
			"name",
			order_by="name asc",
		)

	def _first_account(self, filters):
		return frappe.db.get_value("Account", filters, "name", order_by="name asc")


@frappe.whitelist()
def create_deposit_voucher_draft(money_flow_name: str):
	service = VehicleVoucherService()
	return service.create_deposit_voucher_draft(money_flow_name)


@frappe.whitelist()
def create_final_payment_voucher_draft(money_flow_name: str):
	service = VehicleVoucherService()
	return service.create_final_payment_voucher_draft(money_flow_name)


@frappe.whitelist()
def confirm_voucher_draft(voucher_draft_name: str, review_note: str | None = None):
	service = VehicleVoucherService()
	return service.confirm_voucher_draft(voucher_draft_name, review_note)


@frappe.whitelist()
def reject_voucher_draft(voucher_draft_name: str, reason: str):
	service = VehicleVoucherService()
	return service.reject_voucher_draft(voucher_draft_name, reason)


@frappe.whitelist()
def void_voucher_draft(voucher_draft_name: str, reason: str):
	service = VehicleVoucherService()
	return service.void_voucher_draft(voucher_draft_name, reason)
