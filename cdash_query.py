#!/usr/bin/env python3
"""
CDash API Query Script

This script queries the CDash API for the Spack Testing project.
It supports authentication via token and provides various query capabilities.

Usage:
    python cdash_query.py -p <token> [options]
"""

import argparse
import requests
import json
import sys
from urllib.parse import urlencode


class CDashClient:
    def __init__(self, base_url="https://cdash.spack.io", token=None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()

        if token:
            # CDash may use different auth methods - try both
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'X-API-Token': token,
                'Content-Type': 'application/json'
            })

        # Default project name
        self.default_project = 'Spack Testing'

    def _make_graphql_request(self, query, variables=None):
        """Make a GraphQL request to CDash"""
        url = f"{self.base_url}/graphql"

        payload = {
            'query': query
        }

        if variables:
            payload['variables'] = variables

        print(f"Making GraphQL request to: {url}", file=sys.stderr)
        print(f"Query: {query[:100]}...", file=sys.stderr)

        try:
            response = self.session.post(url, json=payload, timeout=15)
            print(f"Response status: {response.status_code}", file=sys.stderr)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print("Request timed out", file=sys.stderr)
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}", file=sys.stderr)
            print(f"Response text: {response.text if 'response' in locals() else 'No response'}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}", file=sys.stderr)
            print(f"Response text: {response.text}", file=sys.stderr)
            return None

    def list_projects(self):
        """List all available projects"""
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
        return self._make_graphql_request(query)

    def get_builds(self, date=None, filtercount=50):
        """Get builds for the project"""
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
                        }
                    }
                }
            }
        }
        """
        variables = {
            'projectName': self.default_project,
            'first': filtercount
        }
        return self._make_graphql_request(query, variables)

    def get_build_defects(self, build_id):
        """Get defects for a specific build"""
        query = """
        query GetBuildDefects($buildId: ID!) {
            build(id: $buildId) {
                id
                name
                stamp
                startTime
                endTime
            }
        }
        """
        variables = {
            'buildId': build_id
        }
        return self._make_graphql_request(query, variables)

    def get_coverage(self, build_id=None):
        """Get coverage information"""
        query = """
        query GetCoverage($projectName: String!) {
            project(name: $projectName) {
                id
                name
                buildCount
                builds(first: 10) {
                    edges {
                        node {
                            id
                            name
                            startTime
                        }
                    }
                }
            }
        }
        """
        variables = {
            'projectName': self.default_project
        }
        return self._make_graphql_request(query, variables)

    def get_project_info(self):
        """Get project information"""
        query = """
        query GetProjectInfo($projectName: String!) {
            project(name: $projectName) {
                id
                name
                description
                homeurl
                visibility
                buildCount
                mostRecentBuild {
                    id
                    name
                    stamp
                    startTime
                }
                builds(first: 5) {
                    edges {
                        node {
                            id
                            name
                            stamp
                            startTime
                        }
                    }
                }
            }
        }
        """
        variables = {
            'projectName': self.default_project
        }
        return self._make_graphql_request(query, variables)

    def get_test_failures_by_group(self, group_name, limit=50, build_filter=None):
        """Get test failures for builds in a specific group, optionally filtered by build name"""
        # First, get builds without test details to avoid server errors
        query = """
        query GetTestFailuresByGroup($projectName: String!, $first: Int) {
            project(name: $projectName) {
                builds(first: $first) {
                    edges {
                        node {
                            id
                            name
                            stamp
                            startTime
                            failedTestsCount
                            site {
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        # Fetch more builds initially to improve chances of finding failures
        variables = {
            'projectName': self.default_project,
            'first': limit * 10  # Fetch 10x more builds to find ones with failures
        }

        result = self._make_graphql_request(query, variables)

        if not result or 'data' not in result:
            print(f"Error: No data in result: {result}", file=sys.stderr)
            return result

        if not result['data']['project'] or not result['data']['project']['builds']:
            print(f"Error: No builds data in result: {result['data']}", file=sys.stderr)
            return result

        # Filter builds by group name and only include those with failed tests
        all_builds = []
        builds_with_failures = []

        for edge in result['data']['project']['builds']['edges']:
            build = edge['node']
            build_name = build['name']

            # Check if this build belongs to the specified group
            group_match = f"({group_name})" in build_name if group_name else True

            # Check if build name matches the filter pattern
            name_match = True
            if build_filter:
                name_match = build_filter.lower() in build_name.lower()

            if group_match and name_match:
                build['failed_tests'] = []  # Will fetch details separately if needed
                build['has_failures'] = build['failedTestsCount'] > 0
                all_builds.append(build)

                # Collect builds with failures
                if build['has_failures']:
                    builds_with_failures.append(build)

        # Now fetch test details for builds with failures
        for build in builds_with_failures[:limit]:
            test_details = self._get_test_details_for_build(build['id'])
            # Enhance with REST API details for full error output
            for test in test_details:
                if test.get('id'):
                    rest_details = self.get_test_details_via_rest(test['id'])
                    if rest_details and 'test' in rest_details:
                        test['error_output'] = rest_details['test'].get('output', '')
                        test['command'] = rest_details['test'].get('command', '')
            build['failed_tests'] = test_details  # Always assign, even if empty

        return {
            'data': {
                'group': group_name,
                'build_filter': build_filter,
                'all_builds': all_builds[:limit],
                'builds_with_failures': builds_with_failures[:limit]
            }
        }

    def _get_test_details_for_build(self, build_id):
        """Get test details for a specific build"""
        query = """
        query GetTestDetails($buildId: ID!) {
            build(id: $buildId) {
                tests(first: 50) {
                    edges {
                        node {
                            id
                            name
                            status
                            details
                            runningTime
                        }
                    }
                }
            }
        }
        """
        variables = {'buildId': build_id}

        try:
            result = self._make_graphql_request(query, variables)
            if result and 'data' in result and result['data']['build']:
                failed_tests = []
                if result['data']['build']['tests']:
                    for edge in result['data']['build']['tests']['edges']:
                        test = edge['node']
                        if test['status'] == 'FAILED':
                            failed_tests.append(test)
                return failed_tests
        except Exception as e:
            print(f"Error fetching test details for build {build_id}: {e}", file=sys.stderr)

        return []

    def get_test_details_via_rest(self, buildtest_id):
        """Get detailed test information including error output via REST API"""
        url = f"{self.base_url}/api/v1/testDetails.php?buildtestid={buildtest_id}"

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching test details via REST API: {e}", file=sys.stderr)
            return None

    def get_test_details(self, test_id):
        """Get detailed information for a specific test (deprecated GraphQL version)"""
        # Use REST API instead
        return self.get_test_details_via_rest(test_id)

    def get_all_test_failures(self, limit=50, build_filter=None):
        """Get test failures for all builds, optionally filtered by build name"""
        return self.get_test_failures_by_group(None, limit, build_filter)


def main():
    parser = argparse.ArgumentParser(
        description='Query CDash API for Spack Testing project',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p YOUR_TOKEN --list-projects
  %(prog)s -p YOUR_TOKEN --test-failures "Data and Vis SDK"
  %(prog)s -p YOUR_TOKEN --test-failures "Machine Learning" --build-filter "py-tensorflow"
  %(prog)s -p YOUR_TOKEN --all-test-failures --build-filter "adios2" --output summary
  %(prog)s -p YOUR_TOKEN --build-filter "vtk@" --output summary
  %(prog)s -p YOUR_TOKEN  # Default: show test failures for Data and Vis SDK
        """
    )

    parser.add_argument('-p', '--token', required=True,
                       help='CDash authentication token')

    parser.add_argument('--base-url', default='https://cdash.spack.io',
                       help='CDash base URL (default: https://cdash.spack.io)')

    # Query options
    parser.add_argument('--list-projects', action='store_true',
                       help='List all available projects')

    parser.add_argument('--get-builds', action='store_true',
                       help='Get builds for the project')

    parser.add_argument('--date',
                       help='Filter builds by date (YYYY-MM-DD format)')

    parser.add_argument('--filtercount', type=int, default=50,
                       help='Number of builds to return (default: 50)')

    parser.add_argument('--build-defects',
                       help='Get defects for specific build ID')

    parser.add_argument('--coverage', action='store_true',
                       help='Get coverage information')

    parser.add_argument('--project-info', action='store_true',
                       help='Get project information')

    parser.add_argument('--test-failures',
                       help='Get test failures for specific build group (e.g., "Data and Vis SDK")')

    parser.add_argument('--all-test-failures', action='store_true',
                       help='Get test failures for all builds (across all groups)')

    parser.add_argument('--build-filter',
                       help='Filter builds by name pattern (e.g., "py-tensorflow", "vtk@", "gcc@11")')

    parser.add_argument('--output', choices=['json', 'summary'], default='json',
                       help='Output format (default: json)')

    parser.add_argument('--test-details',
                       help='Get detailed information for a specific test ID')

    args = parser.parse_args()

    # Create CDash client
    client = CDashClient(base_url=args.base_url, token=args.token)

    result = None

    # Execute requested operation
    if args.list_projects:
        result = client.list_projects()
    elif args.get_builds:
        result = client.get_builds(date=args.date, filtercount=args.filtercount)
    elif args.build_defects:
        result = client.get_build_defects(args.build_defects)
    elif args.coverage:
        result = client.get_coverage()
    elif args.project_info:
        result = client.get_project_info()
    elif args.test_failures:
        result = client.get_test_failures_by_group(args.test_failures, limit=args.filtercount, build_filter=args.build_filter)
    elif args.all_test_failures:
        result = client.get_all_test_failures(limit=args.filtercount, build_filter=args.build_filter)
    elif args.test_details:
        result = client.get_test_details(args.test_details)
    else:
        # Default action: get test failures for Data and Vis SDK
        result = client.get_test_failures_by_group('Data and Vis SDK', limit=args.filtercount, build_filter=args.build_filter)

    # Output results
    if result is not None:
        if args.output == 'json':
            print(json.dumps(result, indent=2))
        else:
            # Summary format - basic interpretation of common responses
            if 'all_builds' in result.get('data', {}):
                # Test failures format
                data = result['data']
                all_builds = data['all_builds']
                builds_with_failures = data['builds_with_failures']
                group_text = f"group '{data['group']}'" if data['group'] else "all groups"
                filter_text = f" (filtered by '{data['build_filter']}')" if data.get('build_filter') else ""
                print(f"Builds in {group_text}{filter_text}:")
                print(f"Found {len(all_builds)} total builds, {len(builds_with_failures)} with failed tests:")
                print()

                # Show builds with failures first, then passing builds
                for build in builds_with_failures:
                    status_text = "❌ FAILING"
                    print(f"Build: {build['name']} [{status_text}]")
                    print(f"  ID: {build['id']}")
                    print(f"  Site: {build['site']['name']}")
                    print(f"  Start Time: {build['startTime']}")
                    print(f"  Failed Tests: {build['failedTestsCount']}")

                    if build['failed_tests']:
                        print("  Failed Tests Details:")
                        for test in build['failed_tests']:
                            runtime = f"{test['runningTime']}s" if test['runningTime'] > 0 else "0s"
                            test_id = test.get('id', 'Unknown')
                            print(f"    - {test['name']} (Runtime: {runtime}, Test ID: {test_id})")

                            # Show command if available
                            if test.get('command'):
                                cmd_preview = test['command'][:150] + "..." if len(test['command']) > 150 else test['command']
                                print(f"      Command: {cmd_preview}")

                            # Show error output if available
                            if test.get('error_output'):
                                output_lines = test['error_output'].strip().split('\n')
                                if len(output_lines) > 10:
                                    print(f"      Error Output (last 10 lines):")
                                    for line in output_lines[-10:]:
                                        if line.strip():
                                            print(f"        {line[:150]}")
                                else:
                                    print(f"      Error Output:")
                                    for line in output_lines:
                                        if line.strip():
                                            print(f"        {line[:150]}")
                            elif test['details'] and test['details'] != 'Completed':
                                print(f"      Error Details: {test['details'][:500]}...")

                            print(f"      Use --test-details {test_id} for full details")
                    print()

                # Optionally show some passing builds for context
                passing_builds = [b for b in all_builds if not b['has_failures']]
                if passing_builds and len(builds_with_failures) < 10:
                    print("Recent passing builds:")
                    for build in passing_builds[:5]:
                        print(f"Build: {build['name']} [✅ PASSING]")
                        print(f"  ID: {build['id']}")
                        print(f"  Site: {build['site']['name']}")
                        print(f"  Start Time: {build['startTime']}")
                        print()

            elif 'builds' in result:
                print(f"Found {len(result['builds'])} builds:")
                for build in result['builds'][:10]:  # Show first 10
                    print(f"  - {build.get('name', 'Unknown')} (ID: {build.get('id', 'N/A')})")
            elif 'data' in result and 'projects' in result['data']:
                projects = result['data']['projects']['edges']
                print(f"Found {len(projects)} projects:")
                for edge in projects:
                    project = edge['node']
                    print(f"  - {project.get('name', 'Unknown')} (Builds: {project.get('buildCount', 0)})")
            else:
                print(json.dumps(result, indent=2))
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
