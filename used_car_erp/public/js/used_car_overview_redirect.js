(function () {
  const overviewRoutes = new Set(["總覽", "Workspaces/總覽", "workspace/總覽"]);
  const dashboardRoute = "used-car-management-dashboard";

  function getRouteString() {
    if (typeof frappe === "undefined") {
      return "";
    }

    if (typeof frappe.get_route_str === "function") {
      return decodeURIComponent(frappe.get_route_str() || "");
    }

    if (typeof frappe.get_route === "function") {
      return decodeURIComponent((frappe.get_route() || []).join("/"));
    }

    return "";
  }

  function redirectOverviewToDashboard() {
    if (typeof frappe === "undefined" || !frappe.set_route) {
      return;
    }

    const routeString = getRouteString();

    if (routeString === dashboardRoute) {
      return;
    }

    if (overviewRoutes.has(routeString)) {
      frappe.set_route(dashboardRoute);
    }
  }

  if (typeof frappe !== "undefined" && frappe.router && frappe.router.on) {
    frappe.router.on("change", function () {
      setTimeout(redirectOverviewToDashboard, 0);
    });
  }

  if (typeof frappe !== "undefined" && frappe.ready) {
    frappe.ready(function () {
      setTimeout(redirectOverviewToDashboard, 0);
    });
  }
})();
