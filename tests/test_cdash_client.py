"""Unit tests for CDash client."""

from unittest.mock import Mock, patch
from cdash_mcp_server.cdash_client import CDashClient


class TestCDashClient:
    """Test CDashClient class."""

    def test_client_initialization(self):
        """Test client initialization."""
        client = CDashClient()
        assert client.base_url == "https://open.cdash.org"
        assert "Content-Type" in client.session.headers

    def test_client_custom_base_url(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://custom.cdash.io"
        client = CDashClient(base_url=custom_url)
        assert client.base_url == custom_url

    def test_client_base_url_trailing_slash(self):
        """Test that trailing slashes are removed from base URL."""
        client = CDashClient(base_url="https://custom.cdash.io/")
        assert client.base_url == "https://custom.cdash.io"

    @patch("requests.Session.post")
    def test_execute_query_success(self, mock_post):
        """Test successful GraphQL query execution."""
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
                            }
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = CDashClient()
        query = "query { projects { edges { node { id name } } } }"
        result = client.execute_query(query)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["projects"]["edges"][0]["node"]["name"] == "Test Project"

    @patch("requests.Session.post")
    def test_execute_query_with_variables(self, mock_post):
        """Test query execution with variables."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"project": {"id": "1", "name": "Test Project"}}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = CDashClient()
        query = "query GetProject($name: String!) { project(name: $name) { id name } }"
        variables = {"name": "Test Project"}
        result = client.execute_query(query, variables)

        assert result["success"] is True
        assert result["data"]["project"]["name"] == "Test Project"

    @patch("requests.Session.post")
    def test_execute_query_graphql_errors(self, mock_post):
        """Test query execution with GraphQL errors."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "errors": [{"message": "Field 'invalid' not found"}],
            "data": None,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = CDashClient()
        query = "query { invalid }"
        result = client.execute_query(query)

        assert result["success"] is False
        assert "errors" in result
        assert result["errors"][0]["message"] == "Field 'invalid' not found"

    @patch("requests.Session.post")
    def test_execute_query_timeout(self, mock_post):
        """Test query execution with timeout."""
        import requests

        mock_post.side_effect = requests.exceptions.Timeout()

        client = CDashClient()
        query = "query { projects { edges { node { id } } } }"
        result = client.execute_query(query, timeout=5)

        assert result["success"] is False
        assert "errors" in result
        assert result["errors"][0]["type"] == "timeout"

    @patch("requests.Session.post")
    def test_execute_query_network_error(self, mock_post):
        """Test query execution with network error."""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        client = CDashClient()
        query = "query { projects { edges { node { id } } } }"
        result = client.execute_query(query)

        assert result["success"] is False
        assert "errors" in result
        assert result["errors"][0]["type"] == "network_error"

    @patch("requests.Session.post")
    def test_get_schema(self, mock_post):
        """Test schema introspection."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "__schema": {
                    "queryType": {"name": "Query"},
                    "types": [{"name": "Project", "kind": "OBJECT"}],
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = CDashClient()
        result = client.get_schema()

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["__schema"]["queryType"]["name"] == "Query"
