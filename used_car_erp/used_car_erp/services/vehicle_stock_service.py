import frappe
from frappe.utils import flt, nowdate

from used_car_erp.used_car_erp.services.vehicle_item_service import VehicleItemService


FALLBACK_STOCK_ENTRY_DIFFERENCE_ACCOUNT = "0100005-UC - 中古車銷貨成本 - O"


class VehicleStockService:
	def stock_in_vehicle(self, vehicle_name: str):
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		vehicle.check_permission("write")
		self._validate_vehicle(vehicle)

		if vehicle.stock_entry:
			return self._already_stocked_response(vehicle, "此車輛已有入庫單，不會重複正式入庫。")

		if vehicle.serial_no:
			return self._already_stocked_response(vehicle, "此車輛已有 ERPNext 序號，不會重複建立入庫資料。")

		item = frappe.get_doc("Item", vehicle.item)
		self._ensure_item_can_receive_serial_stock(item)
		self._validate_existing_serial_no(vehicle, item)

		stock_entry = frappe.get_doc(self._build_stock_entry_doc(vehicle)).insert()
		stock_entry.submit()
		self._validate_submitted_stock_entry(stock_entry, vehicle)

		serial_no = self._get_submitted_serial_no(vehicle)
		self._update_vehicle_stock_links(vehicle, stock_entry.name, serial_no)

		return {
			"stock_entry": stock_entry.name,
			"serial_no": serial_no,
			"status": "庫存中",
			"created": True,
			"message": "已建立並提交 ERPNext Stock Entry，車輛已正式入庫。",
		}

	def _validate_vehicle(self, vehicle):
		if not vehicle.item:
			frappe.throw("車輛必須先建立並連結 ERPNext 商品，才能正式入庫。")
		if not frappe.db.exists("Item", vehicle.item):
			frappe.throw("車輛連結的 ERPNext 商品不存在，請先修正商品連結。")
		if not vehicle.vin:
			frappe.throw("車輛必須填寫車身號碼 / VIN，才能正式入庫並建立 Serial No。")
		if not vehicle.stock_warehouse:
			frappe.throw("車輛必須選擇入庫倉庫，才能正式入庫。")
		if not frappe.db.exists("Warehouse", {"name": vehicle.stock_warehouse, "is_group": 0}):
			frappe.throw("入庫倉庫必須是 ERPNext 非群組 Warehouse。")
		if flt(vehicle.purchase_price) <= 0:
			frappe.throw("車輛採購車價必須大於 0，才能作為正式入庫 valuation rate。")
		if vehicle.status in ("已售出", "封存"):
			frappe.throw("已售出或封存車輛不可正式入庫。")

	def _ensure_item_can_receive_serial_stock(self, item):
		if not item.is_stock_item:
			frappe.throw("車輛連結的 ERPNext 商品必須是 Stock Item。")

		if item.meta.has_field("has_serial_no") and not item.has_serial_no:
			# 正式入庫前才啟用序號，避免 Item 服務提早建立無庫存序號資料。
			item.db_set("has_serial_no", 1)

	def _validate_existing_serial_no(self, vehicle, item):
		if not frappe.db.exists("Serial No", vehicle.vin):
			return

		serial_item = frappe.db.get_value("Serial No", vehicle.vin, "item_code")
		if serial_item != item.name:
			frappe.throw("此 VIN 已存在於其他 ERPNext Item 的 Serial No，不可用於本車輛入庫。")

	def _build_stock_entry_doc(self, vehicle):
		item_row = {
			"item_code": vehicle.item,
			"qty": 1,
			"t_warehouse": vehicle.stock_warehouse,
			"basic_rate": vehicle.purchase_price,
			"serial_no": vehicle.vin,
			"allow_zero_valuation_rate": 0,
		}
		if self._stock_entry_detail_has_expense_account():
			item_row["expense_account"] = self._resolve_stock_entry_difference_account(vehicle)

		stock_entry_doc = {
			"doctype": "Stock Entry",
			"purpose": "Material Receipt",
			"posting_date": nowdate(),
			"items": [item_row],
		}

		stock_entry_meta = frappe.get_meta("Stock Entry")
		if stock_entry_meta.has_field("stock_entry_type"):
			stock_entry_doc["stock_entry_type"] = "Material Receipt"

		return stock_entry_doc

	def _resolve_company_for_stock_entry(self, vehicle):
		if getattr(vehicle, "company", None):
			return vehicle.company
		if getattr(vehicle, "stock_warehouse", None) and frappe.db.exists("Warehouse", vehicle.stock_warehouse):
			company = frappe.db.get_value("Warehouse", vehicle.stock_warehouse, "company")
			if company:
				return company
		return "OO"

	def _resolve_stock_entry_difference_account(self, vehicle):
		company = self._resolve_company_for_stock_entry(vehicle)
		company_account = None
		if frappe.db.exists("Company", company) and frappe.get_meta("Company").has_field("stock_adjustment_account"):
			company_account = frappe.db.get_value("Company", company, "stock_adjustment_account")
			if company_account:
				self._validate_difference_account(company_account, company)
				return company_account

		try:
			self._validate_difference_account(FALLBACK_STOCK_ENTRY_DIFFERENCE_ACCOUNT, company)
		except Exception:
			frappe.throw(
				"找不到可用的 Stock Entry Difference Account，請先設定 Company.stock_adjustment_account 或確認 0100005-UC - 中古車銷貨成本 - O。"
			)
		return FALLBACK_STOCK_ENTRY_DIFFERENCE_ACCOUNT

	def _validate_difference_account(self, account, company):
		if not account or not frappe.db.exists("Account", account):
			frappe.throw(
				"找不到可用的 Stock Entry Difference Account，請先設定 Company.stock_adjustment_account 或確認 0100005-UC - 中古車銷貨成本 - O。"
			)

		account_doc = frappe.get_doc("Account", account)
		if account_doc.company != company:
			frappe.throw(f"Stock Entry Difference Account {account} 必須屬於公司 {company}。")
		if int(account_doc.is_group or 0):
			frappe.throw(f"Stock Entry Difference Account {account} 必須是非群組會計科目。")
		if int(account_doc.disabled or 0):
			frappe.throw(f"Stock Entry Difference Account {account} 不可停用。")
		if getattr(account_doc, "root_type", None) != "Expense":
			frappe.throw(f"Stock Entry Difference Account {account} root_type 必須是 Expense。")

	def _stock_entry_detail_has_expense_account(self):
		return frappe.get_meta("Stock Entry Detail").has_field("expense_account")

	def _validate_submitted_stock_entry(self, stock_entry, vehicle):
		if stock_entry.docstatus != 1:
			frappe.throw("Stock Entry 未成功提交，車輛不可回寫為庫存中。")

		serial_no = self._get_submitted_serial_no(vehicle)
		serial_item = frappe.db.get_value("Serial No", serial_no, "item_code")
		if serial_item != vehicle.item:
			frappe.throw("Stock Entry 提交後的 Serial No 未正確對應車輛 Item。")

	def _get_submitted_serial_no(self, vehicle):
		if frappe.db.exists("Serial No", vehicle.vin):
			return vehicle.vin

		# ERPNext v15 若要求 Serial and Batch Bundle 而未建立 Serial No，必須停止避免庫存與序號不一致。
		frappe.throw("Stock Entry 已提交但未建立 VIN 對應 Serial No，請檢查 ERPNext Serial and Batch Bundle 流程。")

	def _update_vehicle_stock_links(self, vehicle, stock_entry_name: str, serial_no: str):
		# 只回寫正式入庫產物，避免覆寫車輛編號、Item、發票、成本或毛利等其他模組資料。
		frappe.db.set_value(
			"Used Car Vehicle",
			vehicle.name,
			{
				"serial_no": serial_no,
				"stock_entry": stock_entry_name,
				"status": "庫存中",
			},
		)

	def _already_stocked_response(self, vehicle, message: str):
		return {
			"stock_entry": vehicle.stock_entry,
			"serial_no": vehicle.serial_no,
			"status": vehicle.status,
			"created": False,
			"message": message,
		}


@frappe.whitelist()
def stock_in_vehicle(vehicle_name: str):
	service = VehicleStockService()
	return service.stock_in_vehicle(vehicle_name)


def verify_vehicle_stock_service():
	service = VehicleStockService()
	item_service = VehicleItemService()
	vehicle = None
	item_name = None
	stock_entry_name = None
	serial_no = None
	item_existed_before = False
	serial_existed_before = False
	verification = {"cleaned_up": False}

	purchase_invoice_count = frappe.db.count("Purchase Invoice")
	sales_invoice_count = frappe.db.count("Sales Invoice")
	payment_entry_count = frappe.db.count("Payment Entry")
	warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name", order_by="name asc")
	if not warehouse:
		frappe.throw("找不到可用的非群組 Warehouse，無法驗證正式入庫服務。")

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": "VERIFY-STOCK",
				"vin": f"VERIFY-STOCK-{frappe.generate_hash(length=10)}",
				"purchase_price": 300000,
				"stock_warehouse": warehouse,
			}
		).insert()
		stock_no = vehicle.stock_no
		item_existed_before = bool(frappe.db.exists("Item", stock_no))
		serial_existed_before = bool(frappe.db.exists("Serial No", vehicle.vin))

		item_result = item_service.create_item_for_vehicle(vehicle.name)
		item_name = item_result.get("item")
		result = service.stock_in_vehicle(vehicle.name)
		stock_entry_name = result.get("stock_entry")
		serial_no = result.get("serial_no")

		vehicle.reload()
		stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
		serial_item = frappe.db.get_value("Serial No", serial_no, "item_code")

		if not stock_entry_name or stock_entry.docstatus != 1:
			frappe.throw("Vehicle Stock Service verification did not submit Stock Entry.")
		if vehicle.serial_no != serial_no:
			frappe.throw("Vehicle Stock Service verification did not write back serial_no.")
		if vehicle.stock_entry != stock_entry_name:
			frappe.throw("Vehicle Stock Service verification did not write back stock_entry.")
		if vehicle.status != "庫存中":
			frappe.throw("Vehicle Stock Service verification did not update status to 庫存中.")
		if serial_item != vehicle.item:
			frappe.throw("Vehicle Stock Service verification Serial No item_code mismatch.")
		if frappe.db.count("Purchase Invoice") != purchase_invoice_count:
			frappe.throw("Vehicle Stock Service must not create Purchase Invoice.")
		if frappe.db.count("Sales Invoice") != sales_invoice_count:
			frappe.throw("Vehicle Stock Service must not create Sales Invoice.")
		if frappe.db.count("Payment Entry") != payment_entry_count:
			frappe.throw("Vehicle Stock Service must not create Payment Entry.")

		verification = {
			"vehicle_name": vehicle.name,
			"stock_no": stock_no,
			"item": item_name,
			"stock_entry": stock_entry_name,
			"serial_no": serial_no,
			"status": vehicle.status,
			"stock_entry_submitted": stock_entry.docstatus == 1,
			"serial_no_created": bool(frappe.db.exists("Serial No", serial_no)),
			"cleaned_up": False,
		}
	finally:
		try:
			stock_entry_cancelled = False
			if not stock_entry_name and vehicle and frappe.db.exists("Used Car Vehicle", vehicle.name):
				stock_entry_name = frappe.db.get_value(
					"Stock Entry Detail",
					{"serial_no": vehicle.vin, "item_code": item_name},
					"parent",
				)
			if stock_entry_name and frappe.db.exists("Stock Entry", stock_entry_name):
				stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
				if stock_entry.docstatus == 1:
					stock_entry.cancel()
					stock_entry_cancelled = True
				elif stock_entry.docstatus == 0:
					frappe.delete_doc("Stock Entry", stock_entry_name, force=True)
					stock_entry_cancelled = True
			if vehicle and frappe.db.exists("Used Car Vehicle", vehicle.name):
				frappe.db.set_value(
					"Used Car Vehicle",
					vehicle.name,
					{"serial_no": None, "stock_entry": None, "item": None},
				)
				frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
			if stock_entry_cancelled and not serial_existed_before and serial_no and frappe.db.exists("Serial No", serial_no):
				try:
					frappe.delete_doc("Serial No", serial_no, force=True)
				except Exception:
					# 已取消 Stock Ledger 仍可能保留序號歷史，避免為清理而破壞 ERPNext 資料完整性。
					pass
			if stock_entry_cancelled and not item_existed_before and item_name and frappe.db.exists("Item", item_name):
				frappe.delete_doc("Item", item_name, force=True)
			frappe.db.commit()
			verification["cleaned_up"] = True
		except Exception as exc:
			frappe.db.rollback()
			frappe.throw(f"Vehicle Stock Service verification cleanup failed: {exc}")

	return verification
