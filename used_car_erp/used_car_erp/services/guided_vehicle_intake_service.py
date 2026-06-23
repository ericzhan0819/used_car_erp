import json

import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService


class GuidedVehicleIntakeService:
	SAVEPOINT = "guided_vehicle_intake"

	def run(self, payload: dict) -> dict:
		payload = self._normalize_payload(payload)
		self._validate_payload(payload)

		frappe.db.savepoint(self.SAVEPOINT)
		try:
			vehicle = self._create_vehicle(payload)
			intake_result = VehicleIntakeService().complete_intake(vehicle.name)
			if not intake_result or not intake_result.get("status"):
				frappe.throw("車輛已建立，但入庫流程未回傳有效狀態。")

			preparation_result = VehicleListingService().start_preparation(vehicle.name)
			if not preparation_result or preparation_result.get("status") != "整備中":
				frappe.throw("車輛已完成入庫，但無法進入整備中。")

			vehicle.reload()
			if vehicle.status != "整備中":
				frappe.throw("車輛已完成入庫，但狀態未進入整備中。")

			return {
				"status": "success",
				"vehicle": vehicle.name,
				"vehicle_status": vehicle.status,
				"route": ["Form", "Used Car Vehicle", vehicle.name],
				"message": "車輛已建立並進入整備中",
			}
		except Exception:
			frappe.db.rollback(save_point=self.SAVEPOINT)
			raise

	def _normalize_payload(self, payload):
		if isinstance(payload, str):
			try:
				payload = json.loads(payload)
			except ValueError:
				frappe.throw("新增車輛資料格式錯誤，請重新送出。")
		return payload or {}

	def _validate_payload(self, payload: dict):
		if not isinstance(payload, dict) or not payload:
			frappe.throw("新增車輛資料不可空白。")
		if not payload.get("vin"):
			frappe.throw("車身號碼 / VIN 不可空白。")
		if flt(payload.get("purchase_price")) <= 0:
			frappe.throw("購車價必須大於 0。")

	def _create_vehicle(self, payload: dict):
		vehicle_data = self._build_vehicle_data(payload)
		return frappe.get_doc(vehicle_data).insert()

	def _build_vehicle_data(self, payload: dict) -> dict:
		supplier = payload.get("supplier")
		seller = payload.get("seller") or payload.get("original_owner_name") or payload.get("customer_name")
		vehicle_data = {
			"doctype": "Used Car Vehicle",
			"brand": payload.get("brand"),
			"model": payload.get("model"),
			"year": payload.get("year"),
			"license_plate": payload.get("license_plate"),
			"vin": payload.get("vin"),
			"mileage_km": payload.get("mileage") or payload.get("mileage_km"),
			"color": payload.get("color"),
			"purchase_price": payload.get("purchase_price"),
			"purchase_source_type": payload.get("purchase_source_type") or "個人",
			"purchase_staff": payload.get("purchase_staff"),
			"license_tax_paid": payload.get("license_tax_paid"),
			"fuel_tax_paid": payload.get("fuel_tax_paid"),
			"has_unpaid_loan": payload.get("has_unpaid_loan"),
			"has_tax_penalty": payload.get("has_tax_penalty"),
			"registration_restricted": payload.get("registration_restricted"),
			"insurance_cancelled": payload.get("insurance_cancelled"),
			"plate_cancelled": payload.get("plate_cancelled"),
			"need_document_check": payload.get("need_document_check"),
			"registration_note": payload.get("registration_note"),
		}
		if supplier and frappe.db.exists("Supplier", supplier):
			vehicle_data["supplier"] = supplier
		elif supplier and not seller:
			seller = supplier
		if seller:
			vehicle_data["original_owner_name"] = seller
		return {key: value for key, value in vehicle_data.items() if value is not None}


@frappe.whitelist()
def run_guided_vehicle_intake(payload=None):
	service = GuidedVehicleIntakeService()
	return service.run(payload)
