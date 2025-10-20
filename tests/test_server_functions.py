"""Unit tests for MCP server functions."""

import pytest

from cdash_mcp_server import server


@pytest.mark.unit
class TestServerFunctions:
    """Test MCP server tool functions."""

    def test_list_projects_no_token(self):
        """Test list_projects without token."""
        result = server._list_projects_impl("https://open.cdash.org", "")
        assert "Error" in result
        assert "token parameter is required" in result

    def test_list_projects_success(self, mock_cdash_client, monkeypatch):
        """Test successful project listing."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_projects(self):
            return [
                {
                    "id": "1",
                    "name": "Test Project 1",
                    "description": "First test project",
                    "homeurl": "https://example.com/project1",
                    "visibility": "PUBLIC",
                    "buildCount": 42,
                },
                {
                    "id": "2",
                    "name": "Test Project 2",
                    "description": "Second test project",
                    "homeurl": "https://example.com/project2",
                    "visibility": "PRIVATE",
                    "buildCount": 17,
                },
            ]

        monkeypatch.setattr(CDashClient, "list_projects", mock_list_projects)

        result = server._list_projects_impl("https://test.cdash.org", "test-token")

        assert "Error" not in result
        assert "CDash Projects" in result
        assert "Test Project 1" in result
        assert "Test Project 2" in result
        assert "42" in result  # buildCount from first project

    def test_list_projects_api_error(self, monkeypatch):
        """Test list_projects with API error."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_projects_error(self):
            return None

        monkeypatch.setattr(CDashClient, "list_projects", mock_list_projects_error)

        result = server._list_projects_impl("https://test.cdash.org", "test-token")
        assert "Error" in result or "Failed to retrieve" in result

    def test_list_builds_no_token(self):
        """Test list_builds without token."""
        result = server._list_builds_impl("https://open.cdash.org", "", "Test Project")
        assert "Error" in result
        assert "token parameter is required" in result

    def test_list_builds_no_project_name(self):
        """Test list_builds without project name."""
        result = server._list_builds_impl("https://open.cdash.org", "test-token", "")
        assert "Error" in result
        assert "project_name is required" in result

    def test_list_builds_success(self, monkeypatch):
        """Test successful build listing."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_builds(self, project_name, limit=50):
            return [
                {
                    "id": "100",
                    "name": "build-ubuntu-gcc",
                    "stamp": "20241020-1234",
                    "startTime": "2024-10-20T12:34:00Z",
                    "endTime": "2024-10-20T13:00:00Z",
                    "failedTestsCount": 0,
                    "passedTestsCount": 150,
                    "site": {"name": "ubuntu-runner"},
                },
                {
                    "id": "101",
                    "name": "build-windows-msvc",
                    "stamp": "20241020-1235",
                    "startTime": "2024-10-20T12:35:00Z",
                    "endTime": "2024-10-20T13:15:00Z",
                    "failedTestsCount": 3,
                    "passedTestsCount": 147,
                    "site": {"name": "windows-runner"},
                },
            ]

        monkeypatch.setattr(CDashClient, "list_builds", mock_list_builds)

        result = server._list_builds_impl(
            "https://test.cdash.org", "test-token", "Test Project", limit=10
        )

        assert "Error" not in result
        assert "Builds for Project: Test Project" in result
        assert "build-ubuntu-gcc" in result
        assert "build-windows-msvc" in result
        assert "PASSED" in result
        assert "FAILED" in result

    def test_list_builds_project_not_found(self, monkeypatch):
        """Test list_builds for non-existent project."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_builds_none(self, project_name, limit=50):
            return None

        monkeypatch.setattr(CDashClient, "list_builds", mock_list_builds_none)

        result = server._list_builds_impl(
            "https://test.cdash.org", "test-token", "NonExistent Project"
        )
        assert "Error" in result or "Failed to retrieve" in result

    def test_list_builds_empty_result(self, monkeypatch):
        """Test list_builds with no builds."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_builds_empty(self, project_name, limit=50):
            return []

        monkeypatch.setattr(CDashClient, "list_builds", mock_list_builds_empty)

        result = server._list_builds_impl(
            "https://test.cdash.org", "test-token", "Empty Project"
        )
        assert "No builds found" in result
