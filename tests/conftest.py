"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_cdash_projects():
    """Mock CDash projects response."""
    return [
        {
            "id": "1",
            "name": "Test Project 1",
            "description": "First test project",
            "homeurl": "https://example.com/project1",
            "visibility": "PUBLIC",
            "buildCount": 42
        },
        {
            "id": "2",
            "name": "Test Project 2",
            "description": "Second test project",
            "homeurl": "https://example.com/project2",
            "visibility": "PRIVATE",
            "buildCount": 17
        }
    ]


@pytest.fixture
def mock_cdash_builds():
    """Mock CDash builds response."""
    return [
        {
            "id": "100",
            "name": "build-ubuntu-gcc",
            "stamp": "20241020-1234",
            "startTime": "2024-10-20T12:34:00Z",
            "endTime": "2024-10-20T13:00:00Z",
            "failedTestsCount": 0,
            "passedTestsCount": 150,
            "site": {"name": "ubuntu-runner"}
        },
        {
            "id": "101",
            "name": "build-windows-msvc",
            "stamp": "20241020-1235",
            "startTime": "2024-10-20T12:35:00Z",
            "endTime": "2024-10-20T13:15:00Z",
            "failedTestsCount": 3,
            "passedTestsCount": 147,
            "site": {"name": "windows-runner"}
        }
    ]


@pytest.fixture
def mock_cdash_client(monkeypatch, mock_cdash_projects, mock_cdash_builds):
    """Mock CDashClient for testing."""
    from cdash_mcp_server.cdash_client import CDashClient

    def mock_list_projects(self):
        return mock_cdash_projects

    def mock_list_builds(self, project_name, limit=50):
        return mock_cdash_builds

    monkeypatch.setattr(CDashClient, "list_projects", mock_list_projects)
    monkeypatch.setattr(CDashClient, "list_builds", mock_list_builds)

    return CDashClient(token="test-token")
