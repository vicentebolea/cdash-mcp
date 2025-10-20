"""CDash API Client for querying projects and builds."""

import requests
import json
import sys
from typing import Optional, Dict, Any, List


class CDashClient:
    """Client for interacting with CDash GraphQL API."""

    def __init__(self, base_url: str = "https://cdash.spack.io", token: Optional[str] = None):
        """Initialize CDash client.

        Args:
            base_url: CDash instance base URL
            token: Authentication token for CDash API
        """
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()

        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'X-API-Token': token,
                'Content-Type': 'application/json'
            })

    def _make_graphql_request(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a GraphQL request to CDash.

        Args:
            query: GraphQL query string
            variables: Optional variables for the query

        Returns:
            Response JSON or None on error
        """
        url = f"{self.base_url}/graphql"

        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        try:
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.Timeout, requests.exceptions.RequestException, json.JSONDecodeError, Exception):
            return None

    def list_projects(self) -> Optional[List[Dict[str, Any]]]:
        """List all available projects.

        Returns:
            List of project dictionaries or None on error
        """
        query = """
        query {
            projects {
                edges {
                    node {
                        id
                        name
                        description
                        homeurl
                        visibility
                        buildCount
                    }
                }
            }
        }
        """
        result = self._make_graphql_request(query)

        if result and 'data' in result and 'projects' in result['data']:
            projects = []
            for edge in result['data']['projects']['edges']:
                projects.append(edge['node'])
            return projects
        return None

    def list_builds(self, project_name: str, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """Get builds for a specific project.

        Args:
            project_name: Name of the project
            limit: Maximum number of builds to return

        Returns:
            List of build dictionaries or None on error
        """
        query = """
        query GetBuilds($projectName: String!, $first: Int) {
            project(name: $projectName) {
                builds(first: $first) {
                    edges {
                        node {
                            id
                            name
                            stamp
                            startTime
                            endTime
                            failedTestsCount
                            passedTestsCount
                            site {
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {
            'projectName': project_name,
            'first': limit
        }
        result = self._make_graphql_request(query, variables)

        if result and 'data' in result and result['data'].get('project'):
            builds = []
            if result['data']['project'].get('builds'):
                for edge in result['data']['project']['builds']['edges']:
                    builds.append(edge['node'])
            return builds
        return None
