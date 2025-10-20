"""Unit tests for MCP server functions."""

import pytest
import os
from unittest.mock import patch
from cdash_mcp_server import server


@pytest.mark.unit
class TestServerFunctions:
    """Test MCP server tool functions."""

    def test_list_projects_no_token(self, monkeypatch):
        """Test list_projects without token."""
        # Clear any existing token
        monkeypatch.delenv('CDASH_TOKEN', raising=False)
        server._cdash_client = None

        result = server._list_projects_impl()
        assert "Error" in result
        assert "CDASH_TOKEN" in result

    def test_list_projects_success(self, mock_cdash_client, monkeypatch):
        """Test successful project listing."""
        monkeypatch.setenv('CDASH_TOKEN', 'test-token')
        server._cdash_client = mock_cdash_client

        result = server._list_projects_impl()

        assert "Error" not in result
        assert "CDash Projects" in result
        assert "Test Project 1" in result
        assert "Test Project 2" in result
        assert "42" in result  # buildCount from first project

    def test_list_projects_api_error(self, monkeypatch):
        """Test list_projects with API error."""
        monkeypatch.setenv('CDASH_TOKEN', 'test-token')

        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_projects_error(self):
            return None

        monkeypatch.setattr(CDashClient, "list_projects", mock_list_projects_error)
        server._cdash_client = CDashClient(token="test-token")

        result = server._list_projects_impl()
        assert "Error" in result or "Failed to retrieve" in result

    def test_list_builds_no_token(self, monkeypatch):
        """Test list_builds without token."""
        monkeypatch.delenv('CDASH_TOKEN', raising=False)
        server._cdash_client = None

        result = server._list_builds_impl("Test Project")
        assert "Error" in result
        assert "CDASH_TOKEN" in result

    def test_list_builds_no_project_name(self, monkeypatch):
        """Test list_builds without project name."""
        monkeypatch.setenv('CDASH_TOKEN', 'test-token')
        from cdash_mcp_server.cdash_client import CDashClient
        server._cdash_client = CDashClient(token="test-token")

        result = server._list_builds_impl("")
        assert "Error" in result
        assert "project_name is required" in result

    def test_list_builds_success(self, mock_cdash_client, monkeypatch):
        """Test successful build listing."""
        monkeypatch.setenv('CDASH_TOKEN', 'test-token')
        server._cdash_client = mock_cdash_client

        result = server._list_builds_impl("Test Project", limit=10)

        assert "Error" not in result
        assert "Builds for Project: Test Project" in result
        assert "build-ubuntu-gcc" in result
        assert "build-windows-msvc" in result
        assert "PASSED" in result
        assert "FAILED" in result

    def test_list_builds_project_not_found(self, monkeypatch):
        """Test list_builds for non-existent project."""
        monkeypatch.setenv('CDASH_TOKEN', 'test-token')

        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_builds_none(self, project_name, limit=50):
            return None

        monkeypatch.setattr(CDashClient, "list_builds", mock_list_builds_none)
        server._cdash_client = CDashClient(token="test-token")

        result = server._list_builds_impl("NonExistent Project")
        assert "Error" in result or "Failed to retrieve" in result

    def test_list_builds_empty_result(self, monkeypatch):
        """Test list_builds with no builds."""
        monkeypatch.setenv('CDASH_TOKEN', 'test-token')

        from cdash_mcp_server.cdash_client import CDashClient

        def mock_list_builds_empty(self, project_name, limit=50):
            return []

        monkeypatch.setattr(CDashClient, "list_builds", mock_list_builds_empty)
        server._cdash_client = CDashClient(token="test-token")

        result = server._list_builds_impl("Empty Project")
        assert "No builds found" in result
