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


class TestDepartmentMove:
    def test_cannot_be_own_parent(self, client):
        """Department cannot be its own parent."""
        dept = client.post("/departments/", json={"name": "Solo"})
        dept_id = dept.json()["id"]

        response = client.patch(f"/departments/{dept_id}", json={"parent_id": dept_id})

        assert response.status_code == 409
        assert "own parent" in response.json()["detail"].lower()

    def test_cannot_move_into_descendant(self, client):
        """Cannot move a department into its own subtree (cycle prevention).

        Tree: A -> B -> C
        Action: move A under C
        Expected: 409
        """
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]

        b = client.post("/departments/", json={"name": "B", "parent_id": a_id})
        b_id = b.json()["id"]

        c = client.post("/departments/", json={"name": "C", "parent_id": b_id})
        c_id = c.json()["id"]

        response = client.patch(f"/departments/{a_id}", json={"parent_id": c_id})

        assert response.status_code == 409
        assert "subtree" in response.json()["detail"].lower()

    def test_can_move_to_another_branch(self, client):
        """Can move a department to a different branch.

        Tree:  A -> B,  X -> Y
        Action: move B under X
        Expected: 200, parent_id = X
        """
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]
        b = client.post("/departments/", json={"name": "B", "parent_id": a_id})
        b_id = b.json()["id"]

        x = client.post("/departments/", json={"name": "X"})
        x_id = x.json()["id"]
        client.post("/departments/", json={"name": "Y", "parent_id": x_id})

        response = client.patch(f"/departments/{b_id}", json={"parent_id": x_id})

        assert response.status_code == 200
        assert response.json()["parent_id"] == x_id

    def test_can_make_root(self, client):
        """Can detach from parent and make department root.

        Tree:  A -> B
        Action: set B.parent_id = null
        Expected: 200, parent_id = null
        """
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]
        b = client.post("/departments/", json={"name": "B", "parent_id": a_id})
        b_id = b.json()["id"]

        response = client.patch(f"/departments/{b_id}", json={"parent_id": None})

        assert response.status_code == 200
        assert response.json()["parent_id"] is None

    def test_cannot_move_to_nonexistent_parent(self, client):
        """Cannot move to a department that doesn't exist."""
        dept = client.post("/departments/", json={"name": "A"})
        dept_id = dept.json()["id"]

        response = client.patch(f"/departments/{dept_id}", json={"parent_id": 999})

        assert response.status_code == 404

class TestDeleteDepartmentCascade:
    def test_delete_empty_department(self, client):
        """Delete a department with no children or employees."""
        dept = client.post("/departments/", json={"name": "Empty"})
        dept_id = dept.json()["id"]

        response = client.delete(f"/departments/{dept_id}?mode=cascade")

        assert response.status_code == 204

        # Verify department is gone
        get_response = client.get(f"/departments/{dept_id}")
        assert get_response.status_code == 404

    def test_delete_with_employees(self, client):
        """Cascade delete removes department and its employees."""
        dept = client.post("/departments/", json={"name": "With Employees"})
        dept_id = dept.json()["id"]

        client.post(
            f"/departments/{dept_id}/employees",
            json={"full_name": "Alice", "position": "Dev"},
        )
        client.post(
            f"/departments/{dept_id}/employees",
            json={"full_name": "Bob", "position": "QA"},
        )

        response = client.delete(f"/departments/{dept_id}?mode=cascade")

        assert response.status_code == 204

        # Department and employees are gone
        assert client.get(f"/departments/{dept_id}").status_code == 404

    def test_delete_full_tree(self, client):
        """Cascade delete removes entire subtree with employees at all levels.

        Tree:
            A (has emp_A)
            └── B (has emp_B)
                └── C (has emp_C)

        Delete A → everything gone.
        """
        # Build tree
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]
        client.post(
            f"/departments/{a_id}/employees",
            json={"full_name": "Emp A", "position": "Dev"},
        )

        b = client.post(f"/departments/", json={"name": "B", "parent_id": a_id})
        b_id = b.json()["id"]
        client.post(
            f"/departments/{b_id}/employees",
            json={"full_name": "Emp B", "position": "Dev"},
        )

        c = client.post("/departments/", json={"name": "C", "parent_id": b_id})
        c_id = c.json()["id"]
        client.post(
            f"/departments/{c_id}/employees",
            json={"full_name": "Emp C", "position": "Dev"},
        )

        # Delete root
        response = client.delete(f"/departments/{a_id}?mode=cascade")
        assert response.status_code == 204

        # All departments are gone
        for dep_id in [a_id, b_id, c_id]:
            assert client.get(f"/departments/{dep_id}").status_code == 404


class TestDeleteDepartmentReassign:
    def test_reassign_employees(self, client):
        """Employees move to target department when their department is deleted.

        Tree:  A,  B (has employees)
        Delete B, reassign to A → employees now in A.
        """
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]

        b = client.post("/departments/", json={"name": "B"})
        b_id = b.json()["id"]

        client.post(
            f"/departments/{b_id}/employees/",
            json={"full_name": "Alice", "position": "Dev"},
        )
        client.post(
            f"/departments/{b_id}/employees/",
            json={"full_name": "Bob", "position": "QA"},
        )

        response = client.delete(
            f"/departments/{b_id}?mode=reassign&reassign_to_department_id={a_id}",
        )
        assert response.status_code == 204

        # B is gone
        assert client.get(f"/departments/{b_id}").status_code == 404

        # Employees are now in A
        a_tree = client.get(f"/departments/{a_id}?include_employees=true").json()
        employee_names = [e["full_name"] for e in a_tree["employees"]]
        assert "Alice" in employee_names
        assert "Bob" in employee_names

    def test_reassign_children_move_up(self, client):
        """Child departments move to grandparent when parent is deleted.

        Tree:  A → B → C
        Delete B, reassign employees to A → C becomes child of A.
        """
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]

        b = client.post("/departments/", json={"name": "B", "parent_id": a_id})
        b_id = b.json()["id"]

        c = client.post("/departments/", json={"name": "C", "parent_id": b_id})
        c_id = c.json()["id"]

        response = client.delete(
            f"/departments/{b_id}?mode=reassign&reassign_to_department_id={a_id}",
        )
        assert response.status_code == 204

        # B is gone
        assert client.get(f"/departments/{b_id}").status_code == 404

        # C is now child of A
        a_tree = client.get(f"/departments/{a_id}?depth=2").json()
        child_ids = [c["id"] for c in a_tree["children"]]
        assert c_id in child_ids

    def test_reassign_full_tree(self, client):
        """Full reassign scenario: employees + children + employees in children.

        Tree:
            A
            └── B (has emp_B)
                └── C (has emp_C)

        Delete B, reassign to A:
        - emp_B → A
        - C → child of A (with emp_C intact)
        """
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]

        b = client.post("/departments/", json={"name": "B", "parent_id": a_id})
        b_id = b.json()["id"]
        client.post(
            f"/departments/{b_id}/employees/",
            json={"full_name": "Emp B", "position": "Dev"},
        )

        c = client.post("/departments/", json={"name": "C", "parent_id": b_id})
        c_id = c.json()["id"]
        client.post(
            f"/departments/{c_id}/employees/",
            json={"full_name": "Emp C", "position": "QA"},
        )

        response = client.delete(
            f"/departments/{b_id}?mode=reassign&reassign_to_department_id={a_id}",
        )
        assert response.status_code == 204

        # B is gone
        assert client.get(f"/departments/{b_id}").status_code == 404

        # A tree check
        a_tree = client.get(f"/departments/{a_id}?depth=3&include_employees=true").json()

        # emp_B moved to A
        a_emp_names = [e["full_name"] for e in a_tree["employees"]]
        assert "Emp B" in a_emp_names

        # C is child of A
        child_ids = [c["id"] for c in a_tree["children"]]
        assert c_id in child_ids

        # emp_C still in C
        c_node = next(c for c in a_tree["children"] if c["id"] == c_id)
        c_emp_names = [e["full_name"] for e in c_node["employees"]]
        assert "Emp C" in c_emp_names

    def test_reassign_without_target(self, client):
        """reassign mode without reassign_to_department_id should fail."""
        dept = client.post("/departments/", json={"name": "A"})
        dept_id = dept.json()["id"]

        response = client.delete(
            f"/departments/{dept_id}?mode=reassign",
        )
        assert response.status_code == 422

    def test_reassign_to_nonexistent(self, client):
        """Reassign to nonexistent department should return 404."""
        dept = client.post("/departments/", json={"name": "A"})
        dept_id = dept.json()["id"]

        response = client.delete(
            f"/departments/{dept_id}?mode=reassign&reassign_to_department_id=999",
        )
        assert response.status_code == 404

    def test_reassign_to_self(self, client):
        """Cannot reassign to the department being deleted."""
        dept = client.post("/departments/", json={"name": "A"})
        dept_id = dept.json()["id"]

        response = client.delete(
            f"/departments/{dept_id}?mode=reassign&reassign_to_department_id={dept_id}",
        )
        assert response.status_code == 409

    def test_reassign_to_descendant(self, client):
        """Cannot reassign to a descendant of the department being deleted.

        Tree:  A → B → C
        Delete B with reassign_to=C → 409.
        """
        a = client.post("/departments/", json={"name": "A"})
        a_id = a.json()["id"]

        b = client.post("/departments/", json={"name": "B", "parent_id": a_id})
        b_id = b.json()["id"]

        c = client.post("/departments/", json={"name": "C", "parent_id": b_id})
        c_id = c.json()["id"]

        response = client.delete(
            f"/departments/{b_id}?mode=reassign&reassign_to_department_id={c_id}",
        )
        assert response.status_code == 409