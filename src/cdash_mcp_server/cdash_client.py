"""CDash API Client for executing GraphQL queries."""

import requests
import json
from typing import Optional, Dict, Any


class CDashClient:
    """Client for interacting with CDash GraphQL API."""

    def __init__(self, base_url: str = "https://open.cdash.org"):
        """Initialize CDash client.

        Args:
            base_url: CDash instance base URL (default: https://open.cdash.org)
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against CDash.

        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            timeout: Request timeout in seconds

        Returns:
            Dictionary with 'success', 'data', and optional 'errors' fields
        """
        url = f"{self.base_url}/graphql"
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            result = response.json()

            # Check for GraphQL errors
            if "errors" in result:
                return {
                    "success": False,
                    "errors": result["errors"],
                    "data": result.get("data"),
                }

            return {"success": True, "data": result.get("data")}

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "errors": [
                    {
                        "message": f"Request timed out after {timeout} seconds",
                        "type": "timeout",
                    }
                ],
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "errors": [
                    {"message": f"Network error: {str(e)}", "type": "network_error"}
                ],
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "errors": [
                    {
                        "message": f"Invalid JSON response: {str(e)}",
                        "type": "json_decode_error",
                    }
                ],
            }
        except Exception as e:
            return {
                "success": False,
                "errors": [
                    {"message": f"Unexpected error: {str(e)}", "type": "unknown_error"}
                ],
            }

    def get_schema(self) -> Dict[str, Any]:
        """Fetch the GraphQL schema introspection.

        Returns:
            Dictionary with schema information or error
        """
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                types {
                    name
                    kind
                    description
                    fields {
                        name
                        description
                        args {
                            name
                            description
                            type {
                                name
                                kind
                                ofType {
                                    name
                                    kind
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        return self.execute_query(introspection_query)
