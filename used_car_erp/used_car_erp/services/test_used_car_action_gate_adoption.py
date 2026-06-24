from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.used_car_action_permission_service import UsedCarActionPermissionError
from used_car_erp.used_car_erp.services.vehicle_money_flow_service import VehicleMoneyFlowService
from used_car_erp.used_car_erp.services.vehicle_reservation_service import VehicleReservationService
from used_car_erp.used_car_erp.services.vehicle_voucher_service import VehicleVoucherService


class TestUsedCarActionGateAdoption(FrappeTestCase):
	def setUp(self):
		self.reservation_service = VehicleReservationService()
		self.money_flow_service = VehicleMoneyFlowService()
		self.voucher_service = VehicleVoucherService()

	def test_create_reservation_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.assert_can_perform_used_car_action",
			"used_car_reservation.create",
			lambda: self.reservation_service.create_reservation("MISSING-VEHICLE", "", "", 0, 0, "INVALID"),
		)

	def test_create_final_payment_for_active_reservation_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.assert_can_perform_used_car_action",
			"used_car_money_flow.final_payment.create",
			lambda: self.reservation_service.create_final_payment_for_active_reservation("MISSING-VEHICLE", 0, "INVALID"),
		)

	def test_complete_active_reservation_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.assert_can_perform_used_car_action",
			"used_car_reservation.complete_sale",
			lambda: self.reservation_service.complete_active_reservation("MISSING-VEHICLE"),
		)

	def test_cancel_reservation_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.assert_can_perform_used_car_action",
			"used_car_reservation.cancel",
			lambda: self.reservation_service.cancel_reservation("MISSING-RESERVATION", ""),
		)

	def test_cancel_active_reservation_for_vehicle_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_reservation_service.assert_can_perform_used_car_action",
			"used_car_reservation.cancel",
			lambda: self.reservation_service.cancel_active_reservation_for_vehicle("MISSING-VEHICLE", ""),
		)

	def test_create_deposit_money_flow_from_reservation_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.assert_can_perform_used_car_action",
			"used_car_money_flow.deposit.create",
			lambda: self.money_flow_service.create_deposit_money_flow_from_reservation("MISSING-RESERVATION"),
		)

	def test_create_final_payment_money_flow_from_reservation_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_money_flow_service.assert_can_perform_used_car_action",
			"used_car_money_flow.final_payment.create",
			lambda: self.money_flow_service.create_final_payment_money_flow_from_reservation("MISSING-RESERVATION", 0, "INVALID"),
		)

	def test_confirm_voucher_draft_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_voucher_service.assert_can_perform_used_car_action",
			"used_car_voucher_draft.confirm",
			lambda: self.voucher_service.confirm_voucher_draft("MISSING-VOUCHER-DRAFT"),
		)

	def test_reject_voucher_draft_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_voucher_service.assert_can_perform_used_car_action",
			"used_car_voucher_draft.reject",
			lambda: self.voucher_service.reject_voucher_draft("MISSING-VOUCHER-DRAFT", ""),
		)

	def test_void_voucher_draft_gate_blocks_first(self):
		self._assert_gate_blocks_first(
			"used_car_erp.used_car_erp.services.vehicle_voucher_service.assert_can_perform_used_car_action",
			"used_car_voucher_draft.void",
			lambda: self.voucher_service.void_voucher_draft("MISSING-VOUCHER-DRAFT", ""),
		)

	def _assert_gate_blocks_first(self, patch_target, expected_action, callback):
		with patch(
			patch_target,
			side_effect=UsedCarActionPermissionError("blocked by test"),
		) as gate:
			with self.assertRaises(UsedCarActionPermissionError):
				callback()

		gate.assert_called()
		self.assertEqual(gate.call_args.args[0], expected_action)
