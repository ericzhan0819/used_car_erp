import sys
import types
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


class FakeFrappe:
	class ValidationError(Exception):
		pass

	def __init__(self):
		self.created_docs = []
		self.existing_suppliers = set()
		self.savepoints = []
		self.rollback_save_points = []

	def throw(self, message):
		raise self.ValidationError(message)

	def whitelist(self):
		def decorator(fn):
			return fn

		return decorator

	def get_doc(self, data):
		doc = FakeVehicle(data)
		self.created_docs.append(doc)
		return doc

	def exists(self, doctype, name):
		if doctype == "Supplier" and name in self.existing_suppliers:
			return name
		return None

	def savepoint(self, save_point):
		self.savepoints.append(save_point)

	def rollback(self, *, save_point=None):
		self.rollback_save_points.append(save_point)


class FakeVehicle:
	def __init__(self, data):
		self.data = dict(data)
		self.name = data.get("name") or "UCV-GUIDED-0001"
		self.status = data.get("status") or "草稿"

	def insert(self):
		return self

	def reload(self):
		return self


fake_frappe = FakeFrappe()
frappe_module = types.ModuleType("frappe")
frappe_module.ValidationError = fake_frappe.ValidationError
frappe_module.throw = fake_frappe.throw
frappe_module.whitelist = fake_frappe.whitelist
frappe_module.get_doc = fake_frappe.get_doc
frappe_module.db = fake_frappe

frappe_utils_module = types.ModuleType("frappe.utils")
frappe_utils_module.flt = lambda value: float(value or 0)

sys.modules.setdefault("frappe", frappe_module)
sys.modules.setdefault("frappe.utils", frappe_utils_module)

vehicle_intake_module = types.ModuleType("used_car_erp.used_car_erp.services.vehicle_intake_service")
vehicle_listing_module = types.ModuleType("used_car_erp.used_car_erp.services.vehicle_listing_service")


class FakeVehicleIntakeService:
	calls = []
	fail = False

	def complete_intake(self, vehicle_name):
		self.calls.append(vehicle_name)
		if self.fail:
			raise RuntimeError("intake failed")
		return {"status": "庫存中"}


class FakeVehicleListingService:
	calls = []
	fail = False

	def start_preparation(self, vehicle_name):
		self.calls.append(vehicle_name)
		if self.fail:
			raise RuntimeError("preparation failed")
		fake_frappe.created_docs[-1].status = "整備中"
		return {"status": "整備中"}


vehicle_intake_module.VehicleIntakeService = FakeVehicleIntakeService
vehicle_listing_module.VehicleListingService = FakeVehicleListingService
sys.modules.setdefault("used_car_erp.used_car_erp.services.vehicle_intake_service", vehicle_intake_module)
sys.modules.setdefault("used_car_erp.used_car_erp.services.vehicle_listing_service", vehicle_listing_module)

from used_car_erp.used_car_erp.services.guided_vehicle_intake_service import GuidedVehicleIntakeService


def reset_fakes():
	fake_frappe.created_docs = []
	fake_frappe.existing_suppliers = set()
	fake_frappe.savepoints = []
	fake_frappe.rollback_save_points = []
	FakeVehicleIntakeService.calls = []
	FakeVehicleIntakeService.fail = False
	FakeVehicleListingService.calls = []
	FakeVehicleListingService.fail = False


def valid_payload(**overrides):
	payload = {
		"brand": "Toyota",
		"model": "Altis",
		"year": 2020,
		"license_plate": "ABC-1234",
		"vin": "VIN-GUIDED-001",
		"mileage": 60000,
		"color": "白",
		"purchase_price": 300000,
		"purchase_staff": "buyer@example.com",
	}
	payload.update(overrides)
	return payload


def assert_raises_validation(fn):
	try:
		fn()
	except fake_frappe.ValidationError:
		return
	raise AssertionError("expected frappe.ValidationError")


def test_empty_payload_is_rejected():
	reset_fakes()
	assert_raises_validation(lambda: GuidedVehicleIntakeService().run({}))


def test_missing_vin_is_rejected():
	reset_fakes()
	assert_raises_validation(lambda: GuidedVehicleIntakeService().run(valid_payload(vin="")))


def test_non_positive_purchase_price_is_rejected():
	reset_fakes()
	for purchase_price in (None, 0, -1):
		assert_raises_validation(lambda purchase_price=purchase_price: GuidedVehicleIntakeService().run(valid_payload(purchase_price=purchase_price)))


def test_blank_purchase_source_type_defaults_to_personal():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload(purchase_source_type=""))
	assert fake_frappe.created_docs[0].data["purchase_source_type"] == "個人"


def test_seller_free_text_sets_original_owner_name():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload(seller="測試車主"))
	data = fake_frappe.created_docs[0].data
	assert data["original_owner_name"] == "測試車主"
	assert "supplier" not in data


def test_customer_name_free_text_sets_original_owner_name():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload(customer_name="測試客戶"))
	data = fake_frappe.created_docs[0].data
	assert data["original_owner_name"] == "測試客戶"
	assert "supplier" not in data


def test_missing_supplier_is_not_written_to_supplier_link():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload(supplier="不存在供應商", seller="測試車主"))
	data = fake_frappe.created_docs[0].data
	assert "supplier" not in data
	assert data["original_owner_name"] == "測試車主"


def test_missing_supplier_falls_back_to_original_owner_name():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload(supplier="舊 payload 車主"))
	data = fake_frappe.created_docs[0].data
	assert "supplier" not in data
	assert data["original_owner_name"] == "舊 payload 車主"


def test_existing_supplier_is_written_to_supplier_link():
	reset_fakes()
	fake_frappe.existing_suppliers = {"既有供應商"}
	GuidedVehicleIntakeService().run(valid_payload(supplier="既有供應商", seller="測試車主"))
	data = fake_frappe.created_docs[0].data
	assert data["supplier"] == "既有供應商"
	assert data["original_owner_name"] == "測試車主"


def test_service_calls_existing_intake_service():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload())
	assert FakeVehicleIntakeService.calls == ["UCV-GUIDED-0001"]


def test_service_calls_existing_preparation_service():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload())
	assert FakeVehicleListingService.calls == ["UCV-GUIDED-0001"]


def test_success_returns_vehicle_route_and_status():
	reset_fakes()
	result = GuidedVehicleIntakeService().run(valid_payload())
	assert result == {
		"status": "success",
		"vehicle": "UCV-GUIDED-0001",
		"vehicle_status": "整備中",
		"route": ["Form", "Used Car Vehicle", "UCV-GUIDED-0001"],
		"message": "車輛已建立並進入整備中",
	}
	assert fake_frappe.savepoints == ["guided_vehicle_intake"]
	assert fake_frappe.rollback_save_points == []


def test_success_calls_create_intake_and_preparation_in_order():
	reset_fakes()
	GuidedVehicleIntakeService().run(valid_payload())
	assert fake_frappe.created_docs[0].name == "UCV-GUIDED-0001"
	assert FakeVehicleIntakeService.calls == ["UCV-GUIDED-0001"]
	assert FakeVehicleListingService.calls == ["UCV-GUIDED-0001"]


def test_intake_failure_rolls_back_savepoint_and_reraises():
	reset_fakes()
	FakeVehicleIntakeService.fail = True
	try:
		GuidedVehicleIntakeService().run(valid_payload())
	except RuntimeError as exc:
		assert str(exc) == "intake failed"
	else:
		raise AssertionError("expected original intake exception")
	assert fake_frappe.rollback_save_points == ["guided_vehicle_intake"]
	assert FakeVehicleListingService.calls == []


def test_preparation_failure_rolls_back_savepoint_and_reraises():
	reset_fakes()
	FakeVehicleListingService.fail = True
	try:
		GuidedVehicleIntakeService().run(valid_payload())
	except RuntimeError as exc:
		assert str(exc) == "preparation failed"
	else:
		raise AssertionError("expected original preparation exception")
	assert fake_frappe.rollback_save_points == ["guided_vehicle_intake"]
	assert FakeVehicleIntakeService.calls == ["UCV-GUIDED-0001"]


def run_tests():
	tests = [
		test_empty_payload_is_rejected,
		test_missing_vin_is_rejected,
		test_non_positive_purchase_price_is_rejected,
		test_blank_purchase_source_type_defaults_to_personal,
		test_seller_free_text_sets_original_owner_name,
		test_customer_name_free_text_sets_original_owner_name,
		test_missing_supplier_is_not_written_to_supplier_link,
		test_missing_supplier_falls_back_to_original_owner_name,
		test_existing_supplier_is_written_to_supplier_link,
		test_service_calls_existing_intake_service,
		test_service_calls_existing_preparation_service,
		test_success_returns_vehicle_route_and_status,
		test_success_calls_create_intake_and_preparation_in_order,
		test_intake_failure_rolls_back_savepoint_and_reraises,
		test_preparation_failure_rolls_back_savepoint_and_reraises,
	]
	for test in tests:
		test()
	print("guided vehicle intake service tests ok")


if __name__ == "__main__":
	run_tests()
