import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate


VALID_VOUCHER_DRAFT_STATUSES = ("待審核", "已入帳", "已退回", "已作廢")


class UsedCarVoucherDraft(Document):
	def before_insert(self):
		if not self.voucher_draft_no:
			self.voucher_draft_no = _get_next_voucher_draft_no()
		if not self.status:
			self.status = "待審核"
		if not self.posting_date:
			self.posting_date = nowdate()

	def validate(self):
		self._prevent_voucher_draft_no_change()
		self._prevent_posted_content_change()
		self._validate_status()
		self._validate_required_fields()
		self._calculate_totals()
		self._validate_lines()
		self._validate_balanced()

	def _prevent_voucher_draft_no_change(self):
		if self.is_new():
			return

		old_voucher_draft_no = frappe.db.get_value("Used Car Voucher Draft", self.name, "voucher_draft_no")
		if old_voucher_draft_no and self.voucher_draft_no != old_voucher_draft_no:
			frappe.throw("傳票草稿編號由系統自動產生，不可手動修改。")

	def _prevent_posted_content_change(self):
		if self.is_new():
			return

		old = frappe.get_doc("Used Car Voucher Draft", self.name)
		if old.status != "已入帳":
			return
		if self.posting_date != old.posting_date or self.memo != old.memo or _line_signature(self.lines) != _line_signature(old.lines):
			frappe.throw("已入帳的傳票草稿不可再修改傳票日期、摘要或分錄明細。")

	def _validate_status(self):
		if self.status not in VALID_VOUCHER_DRAFT_STATUSES:
			frappe.throw("草稿狀態必須是：待審核、已入帳、已退回、已作廢。")

	def _validate_required_fields(self):
		if not self.money_flow:
			frappe.throw("金流紀錄為必填。")
		if not self.lines:
			frappe.throw("傳票草稿至少需要一筆分錄明細。")

	def _calculate_totals(self):
		self.total_debit = sum(flt(line.debit) for line in self.lines)
		self.total_credit = sum(flt(line.credit) for line in self.lines)
		self.difference = flt(self.total_debit) - flt(self.total_credit)

	def _validate_lines(self):
		companies = set()
		for line in self.lines:
			if not line.account:
				frappe.throw("每筆分錄都必須選擇會計科目。")
			debit = flt(line.debit)
			credit = flt(line.credit)
			if debit < 0 or credit < 0:
				frappe.throw("分錄借方 / 貸方不可小於 0。")
			if debit > 0 and credit > 0:
				frappe.throw("同一筆分錄不可同時有借方與貸方金額。")
			if debit == 0 and credit == 0:
				frappe.throw("每筆分錄必須有借方或貸方金額。")

			account = frappe.get_doc("Account", line.account)
			if account.is_group:
				frappe.throw("傳票分錄不可使用群組會計科目。")
			companies.add(account.company)

		if len(companies) > 1:
			frappe.throw("傳票草稿所有會計科目必須屬於同一家公司。")

	def _validate_balanced(self):
		if flt(self.total_debit) != flt(self.total_credit) or flt(self.difference) != 0:
			frappe.throw("傳票草稿借方合計必須等於貸方合計，且借貸差額必須為 0。")


def _line_signature(lines):
	return [(line.account, flt(line.debit), flt(line.credit), line.note) for line in lines]


def _get_next_voucher_draft_no():
	period = nowdate().replace("-", "")[:6]
	prefix = f"VD-{period}-"
	rows = frappe.db.sql(
		"""
		select voucher_draft_no
		from `tabUsed Car Voucher Draft`
		where voucher_draft_no like %s
		""",
		(f"{prefix}%",),
		as_dict=True,
	)

	max_number = 0
	for row in rows:
		try:
			max_number = max(max_number, int(row.voucher_draft_no.replace(prefix, "", 1)))
		except (TypeError, ValueError):
			# 歷史匯入資料若編號格式異常，不應中斷後續傳票草稿建立。
			continue

	return f"{prefix}{max_number + 1:04d}"
