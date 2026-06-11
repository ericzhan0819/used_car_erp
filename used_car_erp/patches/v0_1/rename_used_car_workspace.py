import frappe


def execute():
    old_name = "Used Car Management"
    new_name = "中古車管理"

    old_exists = frappe.db.exists("Workspace", old_name)
    new_exists = frappe.db.exists("Workspace", new_name)

    if old_exists and not new_exists:
        frappe.rename_doc("Workspace", old_name, new_name, force=True)
    elif old_exists and new_exists:
        try:
            frappe.delete_doc("Workspace", old_name, force=True)
        except Exception:
            # 避免舊 Workspace 因依賴無法刪除時仍出現在側邊欄造成路由混亂。
            frappe.db.set_value("Workspace", old_name, "is_hidden", 1)

    if frappe.db.exists("Workspace", new_name):
        frappe.db.set_value("Workspace", new_name, "label", new_name)
        frappe.db.set_value("Workspace", new_name, "title", new_name)
        frappe.db.set_value("Workspace", new_name, "module", "Used Car ERP")
        frappe.db.set_value("Workspace", new_name, "public", 1)
        frappe.db.set_value("Workspace", new_name, "is_hidden", 0)

    frappe.clear_cache()
