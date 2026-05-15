class TestCreateEmployees:
    def test_nonexistent_department(self, client):
        response = client.post(
            "/departments/999/employees/",
            json={
                "full_name": "John Doe",
                "position": "Developer",
            },
        )
        assert response.status_code == 404
        assert "999" in response.json()["detail"]

    def test_empty_full_name(self, client):
        # Create a department first
        dept = client.post("/departments/", json={"name": "Engineering"})
        dept_id = dept.json()["id"]

        response = client.post(
            f"/departments/{dept_id}/employees/",
            json={
                "full_name": "",
                "position": "Developer",
            },
        )
        assert response.status_code == 422

    def test_success(self, client):
        # Create a department first
        dept = client.post("/departments/", json={"name": "Engineering"})
        dept_id = dept.json()["id"]

        response = client.post(
            f"/departments/{dept_id}/employees/",
            json={
                "full_name": "John Doe",
                "position": "Developer",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "John Doe"
        assert data["position"] == "Developer"
        assert data["department_id"] == dept_id
        assert data["hired_at"] is None
        assert "id" in data
        assert "created_at" in data