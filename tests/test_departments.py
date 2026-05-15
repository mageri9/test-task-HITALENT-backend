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