"""
04 Find the correct Object ID for GraphQL query
"""

from main import get_client

PROJECT_ID = "128262a20c"
MODEL_ID = "331e6fa2fb"  # Your model ID

def find_correct_object_id():
    """Find the referenced object ID from the latest version"""
    client = get_client()
    
    print(f"\n{'='*70}")
    print(f"FINDING OBJECT IDs FOR MODEL {MODEL_ID}")
    print(f"{'='*70}\n")
    
    # Get all versions
    versions = client.version.get_versions(
        model_id=MODEL_ID,
        project_id=PROJECT_ID,
        limit=10
    )
    
    if not versions.items:
        print(" No versions found")
        return
    
    print(f"Found {len(versions.items)} version(s):\n")
    
    for i, version in enumerate(versions.items, 1):
        # Get the referenced object ID (THIS is what you need for GraphQL)
        ref_object = (
            getattr(version, "referencedObject", None) or 
            getattr(version, "referenced_object", None)
        )
        
        message = getattr(version, 'message', 'No message')
        
        print(f"{'='*70}")
        print(f"Version {i}:")
        print(f"   Message: {message}")
        print(f"   Version ID: {version.id}")
        print(f"   Referenced Object ID (USE THIS): {ref_object}")
        print(f"\n   Copy this for OBJECT_ID in your script:")
        print(f"     OBJECT_ID = \"{ref_object}\"")
        print(f"{'='*70}\n")

if __name__ == "__main__":
    find_correct_object_id()