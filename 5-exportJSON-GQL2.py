"""
05 Export Speckle Object Data to JSON using GraphQL

This script connects to Speckle's GraphQL API and fetches object data
from a specified project and object ID, then saves it to a JSON file.
"""

import json
import os
from main import get_client
from gql import gql


# TODO: Replace with your project and object IDs
PROJECT_ID = "128262a20c"
OBJECT_ID = "ae564ca949be8abf0f986f039ff8773e"


def query_object_data_graphql(client, project_id: str, object_id: str) -> dict:
    """
    Query object data from Speckle using GraphQL API.
    
    Args:
        client: Authenticated SpeckleClient instance
        project_id: The Speckle project ID
        object_id: The Speckle object ID
    
    Returns:
        Dictionary containing the query result
    """
    query = gql("""
    query GetObjectDataJSON($objectId: String!, $projectId: String!) {
        project(id: $projectId) {
            object(id: $objectId) {
                id
                speckleType
                data
            }
        }
    }
    """)
    
    variables = {
        "projectId": project_id,
        "objectId": object_id
    }
    
    # Execute GraphQL query using the client's HTTP session
    result = client.httpclient.execute(query, variable_values=variables)
    return result


def main():
    """
    Main function to fetch object data and save to JSON file.
    """
    # Authenticate with Speckle
    client = get_client()
    print(f"OK Authenticated with Speckle")
    
    # Execute GraphQL query
    try:
        graphql_result = query_object_data_graphql(client, PROJECT_ID, OBJECT_ID)
        print(f"OK GraphQL query executed successfully")
    except Exception as e:
        print(f" GraphQL query failed: {e}")
        return
    
    project_node = graphql_result.get("project")
    if project_node is None:
        print(" GraphQL returned no project. Check PROJECT_ID and permissions.")
        print(f" Raw response: {graphql_result}")
        return

    object_node = project_node.get("object") if isinstance(project_node, dict) else None
    if object_node is None:
        print(" GraphQL returned no object. Check OBJECT_ID and that it belongs to the project.")
        print(f" Raw response: {graphql_result}")
        return

    # Prepare output data
    output = {
        "projectId": PROJECT_ID,
        "objectId": OBJECT_ID,
        "data": object_node.get("data")
    }
    
    # Save to JSON file in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "object_data.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"OK Saved object data to {output_file}")


if __name__ == "__main__":
    main()
