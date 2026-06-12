import frappe
from frappe.model.document import Document
from frappe.utils import flt

from used_car_erp.used_car_erp.services.vehicle_cost_service import recalculate_vehicle_cost_summary


class UsedCarVehicleCost(Document):
	def validate(self):
		self._validate_amount()
		self._validate_vehicle_exists()

	def after_insert(self):
		recalculate_vehicle_cost_summary(self.vehicle)

	def on_update(self):
		recalculate_vehicle_cost_summary(self.vehicle)

	def on_trash(self):
		if self.vehicle:
			frappe.enqueue(
				"used_car_erp.used_car_erp.services.vehicle_cost_service.recalculate_vehicle_cost_summary",
				vehicle_name=self.vehicle,
				enqueue_after_commit=True,
			)

	def _validate_amount(self):
		if flt(self.amount) < 0:
			# 管理成本不可接受負數，避免單車毛利摘要被反向調整而誤導會計覆核。
			frappe.throw("成本金額不可為負數。")

	def _validate_vehicle_exists(self):
		if self.vehicle and not frappe.db.exists("Used Car Vehicle", self.vehicle):
			frappe.throw("車輛不存在。")
