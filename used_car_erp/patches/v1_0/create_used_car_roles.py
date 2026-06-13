import frappe


ROLES = [
    "Used Car Owner",
    "Used Car Manager",
    "Used Car Procurement",
    "Used Car Sales",
    "Used Car Preparation",
    "Used Car Accounting",
    "Used Car Accounting Manager",
    "Used Car Viewer",
    "Used Car Auditor",
]


def execute():
    for role_name in ROLES:
        if frappe.db.exists("Role", role_name):
            continue

        # 僅建立 Frappe 原生 Role 骨架，避免在敏感欄位完成 permlevel 前誤開 custom DocType 權限。
        role = frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
                "disabled": 0,
            }
        )
        role.insert(ignore_permissions=True)
