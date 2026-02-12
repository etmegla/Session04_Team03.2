"""
07 Automated Speckle Backup System

This script combines GraphQL subscription with automatic JSON exports.
Whenever a new version is created in the project, it automatically:
1. Detects the update via WebSocket
2. Fetches the object data
3. Saves it to a timestamped JSON file

Run this script and leave it running to automatically backup all new versions!
"""

import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from gql import gql, Client
from gql.transport.websockets import WebsocketsTransport
from main import get_client

# Load environment variables
load_dotenv()

# Configuration
YOUR_TOKEN = os.environ.get("SPECKLE_TOKEN")
PROJECT_ID = "128262a20c"
BACKUP_DIR = "speckle_backups"  # Directory to store backups

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

# Subscription query
subscription_query = gql("""
    subscription ProjectVersionsUpdated($projectId: String!) {
        projectVersionsUpdated(id: $projectId) {
            id
            modelId
            type
            version {
                id
                message
                createdAt
                referencedObject
                authorUser {
                    name
                }
            }
        }
    }
""")

# GraphQL query for object data
object_query = gql("""
    query GetObjectDataJSON($objectId: String!, $projectId: String!) {
        project(id: $projectId) {
            id
            name
            object(id: $objectId) {
                id
                speckleType
                totalChildrenCount
                data
            }
        }
    }
""")


def export_object_to_json(client, project_id: str, object_id: str, version_info: dict) -> str:
    """
    Export object data to a timestamped JSON file
    
    Args:
        client: Authenticated SpeckleClient
        project_id: Speckle project ID
        object_id: Referenced object ID from version
        version_info: Version metadata for filename
    
    Returns:
        Path to saved file
    """
    try:
        # Execute GraphQL query
        result = client.httpclient.execute(
            object_query,
            variable_values={
                "projectId": project_id,
                "objectId": object_id
            }
        )
        
        # Validate response
        project_node = result.get("project")
        if not project_node:
            print(f"  ERROR: No project data returned")
            return None
        
        object_node = project_node.get("object")
        if not object_node:
            print(f"  ERROR: No object data returned")
            return None
        
        # Create filename with timestamp and version info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = version_info.get("modelId", "unknown")
        version_id = version_info.get("versionId", "unknown")[:8]  # First 8 chars
        
        # Clean version message for filename (remove special chars)
        message = version_info.get("message") or "backup"  # Handle None messages
        clean_message = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in message)
        clean_message = clean_message[:50]  # Limit length
        
        filename = f"{timestamp}_model-{model_id[:8]}_v-{version_id}_{clean_message}.json"
        filepath = os.path.join(BACKUP_DIR, filename)
        
        # Prepare output data
        output = {
            "metadata": {
                "projectId": project_id,
                "projectName": project_node.get("name"),
                "modelId": model_id,
                "versionId": version_info.get("versionId"),
                "versionMessage": version_info.get("message"),
                "author": version_info.get("author"),
                "createdAt": version_info.get("createdAt"),
                "backupTimestamp": datetime.now().isoformat(),
                "objectId": object_id,
            },
            "object": {
                "id": object_node.get("id"),
                "speckleType": object_node.get("speckleType"),
                "totalChildrenCount": object_node.get("totalChildrenCount"),
                "data": object_node.get("data")
            }
        }
        
        # Save to JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        
        file_size = os.path.getsize(filepath)
        print(f"  OK Saved: {filename}")
        print(f"     Size: {file_size:,} bytes")
        
        return filepath
        
    except Exception as e:
        print(f"  ERROR: Export failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def automated_backup_system():
    """
    Main backup system - subscribes to updates and auto-exports
    """
    backup_count = 0
    reconnect_count = 0
    max_reconnects = 5
    
    while reconnect_count < max_reconnects:
        # Create WebSocket transport
        transport = WebsocketsTransport(
            url="wss://app.speckle.systems/graphql",
            init_payload={
                "Authorization": f"Bearer {YOUR_TOKEN}"
            }
        )
        
        # Create GraphQL client for subscriptions
        ws_client = Client(
            transport=transport,
            fetch_schema_from_transport=False,
        )
        
        # Get REST API client for queries
        rest_client = get_client()
        
        try:
            async with ws_client as session:
                if reconnect_count == 0:
                    print(f"\n{'='*70}")
                    print(f"AUTOMATED SPECKLE BACKUP SYSTEM")
                    print(f"{'='*70}")
                    print(f"Status: Connected to Speckle WebSocket")
                    print(f"Project: {PROJECT_ID}")
                    print(f"Backup Directory: {os.path.abspath(BACKUP_DIR)}")
                    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"\nWaiting for new versions... (Press Ctrl+C to stop)\n")
                else:
                    print(f"\n[RECONNECT] Attempt {reconnect_count} of {max_reconnects}...")
                    await asyncio.sleep(2)  # Wait before reconnecting
                
                try:
                    # Subscribe to version updates
                    async for result in session.subscribe(
                        subscription_query,
                        variable_values={"projectId": PROJECT_ID}
                    ):
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        
                        print(f"\n{'='*70}")
                        print(f"UPDATE DETECTED at {timestamp}")
                        print(f"{'='*70}")
                        
                        data = result.get("projectVersionsUpdated")
                        if not data:
                            print("  WARNING: No data in update")
                            continue
                        
                        update_type = data.get('type')
                        model_id = data.get('modelId')
                        
                        print(f"Update Type: {update_type}")
                        print(f"Model ID: {model_id}")
                        
                        version = data.get('version')
                        if not version:
                            print("  WARNING: No version data")
                            continue
                        
                        version_id = version.get('id')
                        message = version.get('message', 'No message')
                        created_at = version.get('createdAt')
                        ref_object = version.get('referencedObject')
                        
                        author_info = version.get('authorUser', {})
                        author = author_info.get('name', 'Unknown') if author_info else 'Unknown'
                        
                        print(f"\nVersion Details:")
                        print(f"   ID: {version_id}")
                        print(f"   Message: {message}")
                        print(f"   Author: {author}")
                        print(f"   Created: {created_at}")
                        print(f"   Object ID: {ref_object}")
                        
                        # Only backup if it's a version creation and has an object
                        if update_type == "CREATED" and ref_object:
                            print(f"\nStarting backup...")
                            
                            version_info = {
                                "modelId": model_id,
                                "versionId": version_id,
                                "message": message,
                                "author": author,
                                "createdAt": created_at,
                            }
                            
                            filepath = export_object_to_json(
                                rest_client,
                                PROJECT_ID,
                                ref_object,
                                version_info
                            )
                            
                            if filepath:
                                backup_count += 1
                                print(f"\nOK Backup #{backup_count} completed!")
                                print(f"View: https://app.speckle.systems/projects/{PROJECT_ID}/models/{model_id}@{version_id}")
                            else:
                                print(f"\nWARNING: Backup failed")
                        else:
                            print(f"\nSkipping backup (type: {update_type}, has object: {bool(ref_object)})")
                        
                        print(f"{'='*70}")
                        print(f"Still monitoring for updates...\n")
                    
                except asyncio.CancelledError:
                    print(f"\n\nSubscription cancelled")
                    raise
                except KeyboardInterrupt:
                    print(f"\n\nStopping backup system...")
                    raise
                except Exception as sub_error:
                    print(f"\n[WARNING] Subscription error: {sub_error}")
                    reconnect_count += 1
                    if reconnect_count < max_reconnects:
                        print(f"[RECONNECT] Connection lost, retrying in 2 seconds...")
                    continue
            
        except (KeyboardInterrupt, asyncio.CancelledError):
            break
        except Exception as e:
            print(f"\nERROR: {e}")
            reconnect_count += 1
            if reconnect_count < max_reconnects:
                await asyncio.sleep(2)
            continue
        finally:
            await transport.close()
    
    print(f"\n{'='*70}")
    print(f"BACKUP SYSTEM SUMMARY")
    print(f"{'='*70}")
    print(f"Total backups created: {backup_count}")
    print(f"Backup directory: {os.path.abspath(BACKUP_DIR)}")
    print(f"Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    print(f"Starting Automated Backup System...")
    asyncio.run(automated_backup_system())