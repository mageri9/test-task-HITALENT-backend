class TestCreateDepartment:
    def test_success(self, client):
        response = client.post(
            "/departments/",
            json={"name": "Backend"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Backend"
        assert data["parent_id"] is None
        assert "id" in data
        assert "created_at" in data
        assert data["employees"] == []
        assert data["children"] == []

    def test_empty_name(self, client):
        response = client.post("/departments/",json={"name": ""})
        assert response.status_code == 422

    def test_name_too_long(self, client):
        response = client.post("/departments/",json={"name": "A" * 201})
        assert response.status_code == 422

    def test_with_parent(self, client):
        # Create parent
        parent = client.post("/departments/",json={"name": "Engineering"})
        parent_id = parent.json()["id"]

        # Create child
        response = client.post("/departments/", json={"name": "Backend", "parent_id": parent_id})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Backend"
        assert data["parent_id"] == parent_id

    def test_nonexistent_parent(self, client):
        response = client.post("/departments/",json={"name": "Backend", "parent_id": 999})
        assert response.status_code == 404
        assert "999" in response.json()["detail"]


class TestDepartmentNameUniqueness:
    def test_duplicate_name_same_parent(self, client):
        """Two departments with same name under same parent should fail."""
        # Create parent
        parent = client.post("/departments/",json={"name": "Engineering"})
        parent_id = parent.json()["id"]

        # Create first child
        client.post("/departments/", json={"name": "Backend", "parent_id": parent_id})

        # Create duplicate child
        response = client.post("/departments/", json={"name": "Backend", "parent_id": parent_id})

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_same_name_different_parents(self, client):
        """Same name under different parents should be allowed."""
        parent1 = client.post("/departments/", json={"name": "Engineering"})
        parent1_id = parent1.json()["id"]

        parent2 = client.post("/departments/", json={"name": "Product"})
        parent2_id = parent2.json()["id"]

        r1 = client.post("/departments/", json={"name": "Team", "parent_id": parent1_id})
        r2 = client.post("/departments/", json={"name": "Team", "parent_id": parent2_id})

        assert r1.status_code == 201
        assert r2.status_code == 201

    def test_duplicate_root_name(self, client):
        """Two root departments with same name should fail (service-level check)."""
        client.post("/departments/", json={"name": "Operations"})
        response = client.post("/departments/", json={"name": "Operations"})

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()