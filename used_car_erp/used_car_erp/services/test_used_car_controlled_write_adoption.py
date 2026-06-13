from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_money_flow_service import VehicleMoneyFlowService
from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService
from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


class TestUsedCarControlledWriteAdoption(FrappeTestCase):
	def test_create_reservation_uses_controlled_insert_for_reservation(self):
		vehicle = Mock(name="VEH-1", status="上架中", stock_no="STK-1", year=2020, brand="Toyota", model="Altis", item="ITEM", serial_no="SN", stock_entry="SE")
		reservation = Mock(name="RES-1")
		with patch("used_car_erp.used_car_erp.services.vehicle_reservation_service.assert_can_perform_used_car_action"), patch(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.frappe.get_doc", side_effect=[vehicle, reservation]
		), patch("used_car_erp.used_car_erp.services.vehicle_reservation_service.frappe.db.exists", return_value=True), patch(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.frappe.db.commit"
		), patch("used_car_erp.used_car_erp.services.vehicle_reservation_service.insert_service_controlled_doc", return_value=reservation) as controlled_insert, patch(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.db_set_service_controlled_values"
		), patch.object(VehicleReservationService, "_validate_no_active_reservation"), patch.object(
			VehicleReservationService, "_resolve_or_create_customer", return_value="CUST-1"
		), patch(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.VehicleMoneyFlowService"
		) as money_flow_service:
			money_flow_service.return_value.create_deposit_money_flow_from_reservation.return_value = {"money_flow": "MF-1", "voucher_draft": "VD-1"}

			VehicleReservationService().create_reservation("VEH-1", "客戶", "0912345678", 1000, "現金")

		controlled_insert.assert_called_once()
		self.assertEqual(controlled_insert.call_args.kwargs["action"], "used_car_reservation.create")
		self.assertEqual(controlled_insert.call_args.kwargs["allowed_doctype"], "Used Car Reservation")

	def test_deposit_money_flow_uses_controlled_insert_for_money_flow(self):
		reservation = self._reservation_mock()
		money_flow = Mock(name="MF-1", amount=1000, status="待審核")
		with patch("used_car_erp.used_car_erp.services.vehicle_money_flow_service.assert_can_perform_used_car_action"), patch(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.frappe.get_doc", side_effect=[reservation, money_flow, reservation]
		), patch("used_car_erp.used_car_erp.services.vehicle_money_flow_service.frappe.db.exists", return_value=False), patch(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.insert_service_controlled_doc", return_value=money_flow
		) as controlled_insert, patch(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.save_service_controlled_doc"
		), patch("used_car_erp.used_car_erp.services.vehicle_money_flow_service.VehicleVoucherService") as voucher_service:
			voucher_service.return_value.create_deposit_voucher_draft_from_money_flow_service.return_value = "VD-1"

			VehicleMoneyFlowService().create_deposit_money_flow_from_reservation("RES-1")

		controlled_insert.assert_called_once()
		self.assertEqual(controlled_insert.call_args.kwargs["action"], "used_car_money_flow.deposit.create")
		self.assertEqual(controlled_insert.call_args.kwargs["allowed_doctype"], "Used Car Money Flow")

	def test_final_payment_uses_controlled_insert_for_money_flow(self):
		reservation = self._reservation_mock(money_flow="DMF-1", voucher_draft="DVD-1")
		vehicle = Mock(status="保留中")
		money_flow = Mock(name="FMF-1", amount=50000, status="待審核", payment_date="2026-06-14")
		with patch("used_car_erp.used_car_erp.services.vehicle_money_flow_service.assert_can_perform_used_car_action"), patch(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.frappe.get_doc", side_effect=[reservation, vehicle, money_flow, reservation]
		), patch("used_car_erp.used_car_erp.services.vehicle_money_flow_service.frappe.db.exists", return_value=False), patch(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.insert_service_controlled_doc", return_value=money_flow
		) as controlled_insert, patch(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.save_service_controlled_doc"
		), patch("used_car_erp.used_car_erp.services.vehicle_money_flow_service.VehicleVoucherService") as voucher_service:
			voucher_service.return_value.create_final_payment_voucher_draft_from_money_flow_service.return_value = "FVD-1"

			VehicleMoneyFlowService().create_final_payment_money_flow_from_reservation("RES-1", 50000, "現金")

		controlled_insert.assert_called_once()
		self.assertEqual(controlled_insert.call_args.kwargs["action"], "used_car_money_flow.final_payment.create")
		self.assertEqual(controlled_insert.call_args.kwargs["allowed_doctype"], "Used Car Money Flow")

	def test_internal_deposit_voucher_method_passes_controlled_action(self):
		service = VehicleVoucherService()
		with patch.object(service, "_create_deposit_voucher_draft", return_value="VD-1") as builder:
			self.assertEqual(service.create_deposit_voucher_draft_from_money_flow_service("MF-1"), "VD-1")

		builder.assert_called_once_with("MF-1", controlled_action="used_car_money_flow.deposit.create")

	def test_internal_final_voucher_method_passes_controlled_action(self):
		service = VehicleVoucherService()
		with patch.object(service, "_create_final_payment_voucher_draft", return_value="VD-1") as builder:
			self.assertEqual(service.create_final_payment_voucher_draft_from_money_flow_service("MF-1"), "VD-1")

		builder.assert_called_once_with("MF-1", controlled_action="used_car_money_flow.final_payment.create")

	def test_public_deposit_voucher_method_does_not_pass_controlled_action(self):
		service = VehicleVoucherService()
		with patch.object(service, "_create_deposit_voucher_draft", return_value="VD-1") as builder:
			self.assertEqual(service.create_deposit_voucher_draft("MF-1"), "VD-1")

		builder.assert_called_once_with("MF-1")

	def test_public_final_voucher_method_does_not_pass_controlled_action(self):
		service = VehicleVoucherService()
		with patch.object(service, "_create_final_payment_voucher_draft", return_value="VD-1") as builder:
			self.assertEqual(service.create_final_payment_voucher_draft("MF-1"), "VD-1")

		builder.assert_called_once_with("MF-1")

	def _reservation_mock(self, money_flow=None, voucher_draft=None):
		reservation = Mock(
			name="RES-1",
			status="有效",
			deposit_amount=1000,
			vehicle="VEH-1",
			stock_no="STK-1",
			customer="CUST-1",
			customer_name="客戶",
			customer_phone="0912345678",
			payment_date="2026-06-14",
			deposit_date="2026-06-14",
			payment_method="現金",
			payment_reference="REF",
			notes="NOTE",
			money_flow=money_flow,
			voucher_draft=voucher_draft,
			final_money_flow=None,
			final_voucher_draft=None,
		)
		reservation.flags = Mock()
		return reservation
