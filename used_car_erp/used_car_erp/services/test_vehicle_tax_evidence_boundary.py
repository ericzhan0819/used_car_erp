import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.doctype.used_car_vehicle.used_car_vehicle import (
	derive_vehicle_tax_mode_from_purchase_document_type,
)
from used_car_erp.used_car_erp.services.vehicle_cost_service import RESTRICTED_ACCOUNTING_DOCTYPES
from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService


class TestVehicleTaxEvidenceBoundary(FrappeTestCase):
	def test_deductible_invoice_derives_general_invoice_mode(self):
		self.assertEqual(
			derive_vehicle_tax_mode_from_purchase_document_type("統一發票"),
			("一般發票扣抵", "已初步判斷"),
		)

	def test_no_invoice_evidence_derives_article_15_1_mode(self):
		for document_type in ("未取得", "買賣合約", "讓渡書", "匯款紀錄", "收據"):
			self.assertEqual(
				derive_vehicle_tax_mode_from_purchase_document_type(document_type),
				("15-1 特殊扣抵", "已初步判斷"),
			)

	def test_ambiguous_evidence_requires_accounting_review(self):
		for document_type in ("拍場單據", "其他", None, "", "未列入選項"):
			self.assertEqual(
				derive_vehicle_tax_mode_from_purchase_document_type(document_type),
				("待確認", "待確認"),
			)

	def test_vehicle_validate_derives_tax_fields_from_purchase_evidence(self):
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"purchase_document_type": "統一發票",
			}
		)

		vehicle.validate()

		self.assertEqual(vehicle.vehicle_tax_mode, "一般發票扣抵")
		self.assertEqual(vehicle.tax_review_status, "已初步判斷")

	def test_sales_invoice_draft_gate_blocks_ambiguous_purchase_evidence(self):
		vehicle = frappe._dict(purchase_document_type="拍場單據")

		with self.assertRaises(frappe.ValidationError):
			VehicleReservationService()._validate_purchase_evidence_for_sales_invoice_draft(vehicle)

	def test_sales_invoice_draft_gate_allows_invoice_and_no_invoice_evidence(self):
		service = VehicleReservationService()

		self.assertEqual(
			service._validate_purchase_evidence_for_sales_invoice_draft(frappe._dict(purchase_document_type="統一發票")),
			("一般發票扣抵", "已初步判斷"),
		)
		self.assertEqual(
			service._validate_purchase_evidence_for_sales_invoice_draft(frappe._dict(purchase_document_type="未取得")),
			("15-1 特殊扣抵", "已初步判斷"),
		)

	def test_tax_evidence_derivation_does_not_create_formal_documents(self):
		before_counts = self._restricted_doc_counts()

		derive_vehicle_tax_mode_from_purchase_document_type("統一發票")
		derive_vehicle_tax_mode_from_purchase_document_type("未取得")
		derive_vehicle_tax_mode_from_purchase_document_type("拍場單據")

		self.assertEqual(self._restricted_doc_counts(), before_counts)

	def _restricted_doc_counts(self):
		return {
			doctype: frappe.db.count(doctype) if frappe.db.table_exists(doctype) else 0
			for doctype in RESTRICTED_ACCOUNTING_DOCTYPES
		}
