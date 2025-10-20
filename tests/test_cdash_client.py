"""Unit tests for CDash client."""

import pytest
from unittest.mock import Mock, patch
from cdash_mcp_server.cdash_client import CDashClient


class TestCDashClient:
    """Test CDashClient class."""

    def test_client_initialization(self):
        """Test client initialization with token."""
        client = CDashClient(token="test-token")
        assert client.token == "test-token"
        assert client.base_url == "https://cdash.spack.io"
        assert 'Authorization' in client.session.headers

    def test_client_custom_base_url(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://custom.cdash.io"
        client = CDashClient(base_url=custom_url, token="test-token")
        assert client.base_url == custom_url

    @patch('requests.Session.post')
    def test_list_projects_success(self, mock_post):
        """Test successful project listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "projects": {
                    "edges": [
                        {
                            "node": {
                                "id": "1",
                                "name": "Test Project",
                                "description": "A test project",
                                "homeurl": "https://example.com",
                                "visibility": "PUBLIC",
                                "buildCount": 10
                            }
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response

        client = CDashClient(token="test-token")
        projects = client.list_projects()

        assert projects is not None
        assert len(projects) == 1
        assert projects[0]["name"] == "Test Project"
        assert projects[0]["buildCount"] == 10

    @patch('requests.Session.post')
    def test_list_projects_error(self, mock_post):
        """Test project listing with API error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_post.return_value = mock_response

        client = CDashClient(token="test-token")
        projects = client.list_projects()

        assert projects is None

    @patch('requests.Session.post')
    def test_list_builds_success(self, mock_post):
        """Test successful build listing."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "project": {
                    "builds": {
                        "edges": [
                            {
                                "node": {
                                    "id": "100",
                                    "name": "test-build",
                                    "stamp": "20241020-1234",
                                    "startTime": "2024-10-20T12:34:00Z",
                                    "endTime": "2024-10-20T13:00:00Z",
                                    "failedTestsCount": 0,
                                    "passedTestsCount": 50,
                                    "site": {"name": "test-runner"}
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_post.return_value = mock_response

        client = CDashClient(token="test-token")
        builds = client.list_builds("Test Project", limit=10)

        assert builds is not None
        assert len(builds) == 1
        assert builds[0]["name"] == "test-build"
        assert builds[0]["failedTestsCount"] == 0

    @patch('requests.Session.post')
    def test_list_builds_project_not_found(self, mock_post):
        """Test build listing for non-existent project."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "project": None
            }
        }
        mock_post.return_value = mock_response

        client = CDashClient(token="test-token")
        builds = client.list_builds("NonExistent Project")

        assert builds is None
