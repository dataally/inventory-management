"""
Tests for restocking recommendation and restock order endpoints.
"""
import pytest


def recommend(client, budget):
    response = client.get(f"/api/restocking/recommendations?budget={budget}")
    assert response.status_code == 200
    return response.json()


class TestRestockRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_zero_budget_returns_nothing(self, client):
        data = recommend(client, 0)
        assert data["items"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0

    def test_negative_budget_rejected(self, client):
        response = client.get("/api/restocking/recommendations?budget=-5")
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_missing_budget_rejected(self, client):
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    def test_total_never_exceeds_budget(self, client):
        for budget in [50, 500, 2500, 10000, 50000, 1000000]:
            data = recommend(client, budget)
            assert data["total_cost"] <= budget + 0.01
            assert abs(data["total_cost"] + data["remaining_budget"] - budget) < 0.01

    def test_line_structure_and_math(self, client):
        data = recommend(client, 1000000)
        assert len(data["items"]) > 0
        for item in data["items"]:
            for field in ["sku", "name", "category", "warehouse", "trend", "shortfall",
                          "quantity", "unit_cost", "line_cost", "lead_time_days"]:
                assert field in item
            assert item["quantity"] >= 1
            assert item["quantity"] <= item["shortfall"]
            assert abs(item["line_cost"] - item["quantity"] * item["unit_cost"]) < 0.01

    def test_large_budget_covers_full_shortfall(self, client):
        data = recommend(client, 1000000)
        assert all(i["quantity"] == i["shortfall"] for i in data["items"])
        assert abs(data["total_cost"] - data["max_useful_budget"]) < 0.01

    def test_items_with_no_shortfall_excluded(self, client):
        skus = {i["sku"] for i in recommend(client, 1000000)["items"]}
        # PSU-501 has more stock on hand than its forecasted demand
        assert "PSU-501" not in skus

    def test_rising_demand_ranks_first(self, client):
        # Budget big enough for several lines; first line should be a high priority item
        items = recommend(client, 1000000)["items"]
        weights = {"increasing": 1.5, "stable": 1.0, "decreasing": 0.5}
        priorities = [i["shortfall"] * weights[i["trend"]] for i in items]
        assert priorities == sorted(priorities, reverse=True)

    def test_partial_quantity_when_budget_is_tight(self, client):
        full = recommend(client, 1000000)
        small_budget = full["items"][0]["unit_cost"] * 2
        data = recommend(client, small_budget)
        assert len(data["items"]) >= 1
        assert data["items"][0]["quantity"] < data["items"][0]["shortfall"]


class TestRestockOrders:
    """Test suite for POST/GET /api/restock-orders."""

    def make_order(self, client, lines=None, budget=1000000):
        if lines is None:
            items = recommend(client, 1000000)["items"][:2]
            lines = [{"sku": i["sku"], "quantity": i["quantity"]} for i in items]
        return client.post("/api/restock-orders", json={"budget": budget, "lines": lines})

    def test_create_order_success(self, client):
        response = self.make_order(client)
        assert response.status_code == 200
        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Submitted"
        assert len(order["lines"]) == 2
        assert abs(order["total_cost"] - sum(l["line_cost"] for l in order["lines"])) < 0.01

    def test_lead_time_is_max_of_lines(self, client):
        order = self.make_order(client).json()
        assert order["lead_time_days"] == max(l["lead_time_days"] for l in order["lines"])
        assert "T" in order["expected_delivery"]
        assert order["expected_delivery"] > order["submitted_at"]

    def test_mixed_lines_report_multiple(self, client):
        # WDG-001 is Actuators/Tokyo, SNR-420 is Sensors/Tokyo, CTL-330 is Controllers/London
        lines = [{"sku": "WDG-001", "quantity": 1}, {"sku": "CTL-330", "quantity": 1}]
        order = self.make_order(client, lines).json()
        assert order["category"] == "Multiple"
        assert order["warehouse"] == "Multiple"
        # Actuators (14 days) is slower than Controllers (12 days)
        assert order["lead_time_days"] == 14

    def test_single_category_and_warehouse_kept(self, client):
        order = self.make_order(client, [{"sku": "SNR-420", "quantity": 2}]).json()
        assert order["category"] == "Sensors"
        assert order["warehouse"] == "Tokyo"
        assert order["lead_time_days"] == 5

    def test_cost_computed_server_side(self, client):
        order = self.make_order(client, [{"sku": "SNR-420", "quantity": 4}]).json()
        assert abs(order["total_cost"] - 4 * 27.5) < 0.01

    def test_unknown_sku_rejected(self, client):
        response = self.make_order(client, [{"sku": "NOPE-999", "quantity": 1}])
        assert response.status_code == 400
        assert "unknown sku" in response.json()["detail"].lower()

    @pytest.mark.parametrize("quantity", [0, -3])
    def test_non_positive_quantity_rejected(self, client, quantity):
        response = self.make_order(client, [{"sku": "SNR-420", "quantity": quantity}])
        assert response.status_code == 400

    def test_empty_order_rejected(self, client):
        assert self.make_order(client, []).status_code == 400

    def test_over_budget_rejected(self, client):
        response = self.make_order(client, [{"sku": "SNR-420", "quantity": 10}], budget=10)
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()

    def test_orders_listed_newest_first(self, client):
        first = self.make_order(client, [{"sku": "SNR-420", "quantity": 1}]).json()
        second = self.make_order(client, [{"sku": "CTL-330", "quantity": 1}]).json()
        listed = client.get("/api/restock-orders").json()
        assert [o["id"] for o in listed[:2]] == [second["id"], first["id"]]

    def test_orders_do_not_leak_between_tests(self, client):
        assert client.get("/api/restock-orders").json() == []
