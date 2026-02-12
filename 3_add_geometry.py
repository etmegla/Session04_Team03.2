"""
03 - Modify Geometry in a Speckle Model with Nested Properties

This script demonstrates how to find an object by applicationId,
duplicate it with an offset while preserving nested properties (Module, Designer, etc.),
and commit a new version WITH proper organization.

OUTCOME:
- Renames "Unnamed document" to "Old Modules"
- Removes "Layer 01" structure
- Wraps Old/New modules in "Specklepy" collection
- Preserves original BrepX objects
- Assigns designers:
  * Module 01 -> Rania Chihaoui
  * Module 02 -> Eleni Maglari
  * Module 03 -> Eduardo Martinez
"""

import copy
from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects import Base


# TODO: Replace with your project and model IDs
PROJECT_ID = "128262a20c"
MODEL_ID = "331e6fa2fb"

# TODO: Replace with the applicationId of an object to duplicate
TARGET_APPLICATION_ID = "17cc627f-f5df-44d2-908e-1cdaf96fe76c"

# Offset for the duplicated object (move upward = positive Z)
# Note: The model uses millimeters, so 16 meters = 16000 mm
OFFSET_Z = 16000.0

# TODO: Configure nested properties for the NEW duplicated object (Module 02)
NEW_NESTED_PROPERTIES = {
    "Module": "02",
    "Designer": "Eleni Maglari",
}

# Configure properties for the ORIGINAL objects in Old_Modules
OLD_NESTED_PROPERTIES = {
    "01": {
        "Module": "01",
        "Designer": "Rania Chihaoui",
    },
    "03": {
        "Module": "03",
        "Designer": "Eduardo Martinez",
    }
}


# ============================================================================
# STEP 1: HELPER FUNCTIONS FOR FINDING AND COPYING OBJECTS
# ============================================================================

def find_object_by_application_id(obj, target_id: str):
    """
    Recursively search for an object with the given applicationId.
    """
    if not isinstance(obj, Base):
        return None
    
    app_id = getattr(obj, "applicationId", None)
    if app_id == target_id:
        return obj
    
    # Search in child elements
    elements = getattr(obj, "@elements", None) or getattr(obj, "elements", [])
    for element in elements or []:
        found = find_object_by_application_id(element, target_id)
        if found:
            return found
    
    return None


def deep_copy_base_object(obj):
    """
    Create a deep copy of a Speckle Base object, preserving all nested structures.
    """
    new_obj = Base()
    
    # Copy all properties including nested ones
    for key in obj.get_member_names():
        value = getattr(obj, key, None)
        if value is not None:
            try:
                if isinstance(value, Base):
                    new_obj[key] = deep_copy_base_object(value)
                elif isinstance(value, list):
                    new_obj[key] = copy.deepcopy(value)
                elif isinstance(value, dict):
                    new_obj[key] = copy.deepcopy(value)
                else:
                    new_obj[key] = copy.deepcopy(value)
            except Exception as e:
                print(f"  Warning: Could not deep copy {key}: {e}")
                try:
                    new_obj[key] = value
                except:
                    pass
    
    return new_obj


# ============================================================================
# STEP 2: FUNCTIONS FOR OFFSETTING GEOMETRY
# ============================================================================

def offset_geometry(obj, offset_z: float):
    """
    Offset geometry in the Z direction for various geometry types.
    """
    # Handle displayValue (common in Revit objects)
    display_value = getattr(obj, "displayValue", None) or getattr(obj, "@displayValue", None)
    if display_value:
        if isinstance(display_value, list):
            for mesh in display_value:
                offset_mesh_vertices(mesh, offset_z)
        else:
            offset_mesh_vertices(display_value, offset_z)
    
    # Handle direct vertices (for Mesh objects)
    if hasattr(obj, "vertices") and obj.vertices:
        offset_mesh_vertices(obj, offset_z)
    
    # Handle base point / location
    if hasattr(obj, "basePoint"):
        bp = obj.basePoint
        if hasattr(bp, "z"):
            bp.z += offset_z
    
    if hasattr(obj, "location"):
        loc = obj.location
        if hasattr(loc, "z"):
            loc.z += offset_z


def offset_mesh_vertices(mesh, offset_z: float):
    """
    Offset mesh vertices in the Z direction.
    Vertices are stored as flat list: [x1, y1, z1, x2, y2, z2, ...]
    """
    if hasattr(mesh, "vertices") and mesh.vertices:
        new_vertices = []
        for i in range(0, len(mesh.vertices), 3):
            new_vertices.append(mesh.vertices[i])              # x
            new_vertices.append(mesh.vertices[i + 1])          # y
            new_vertices.append(mesh.vertices[i + 2] + offset_z)  # z + offset
        mesh.vertices = new_vertices


# ============================================================================
# STEP 3: FUNCTION TO CREATE DUPLICATED OBJECT WITH NEW PROPERTIES
# ============================================================================

def deep_copy_and_offset(obj, offset_z: float, nested_props: dict = None):
    """
    Create a deep copy of a Speckle object, offset its geometry, and apply custom properties.
    """
    # Create a deep copy preserving all nested structures
    new_obj = deep_copy_base_object(obj)
    
    # Clear the id so a new one is generated
    new_obj.id = None
    
    # Generate a new applicationId for the copy
    import uuid
    new_obj.applicationId = str(uuid.uuid4())
    
    # Apply custom nested properties if provided
    if nested_props:
        new_obj.properties = {
            "Module": nested_props.get("Module"),
            "Designer": nested_props.get("Designer"),
        }
        print(f"  OK Set properties.Module = {nested_props.get('Module')}")
        print(f"  OK Set properties.Designer = {nested_props.get('Designer')}")
    
    # Offset geometry
    offset_geometry(new_obj, offset_z)
    
    return new_obj


# ============================================================================
# STEP 4: FUNCTIONS FOR ORGANIZING THE MODEL STRUCTURE
# ============================================================================

def find_collection_by_name(obj, collection_name: str):
    """
    Find a collection by name in the data tree.
    """
    if not isinstance(obj, Base):
        return None
    
    name = getattr(obj, "name", None)
    if name == collection_name:
        return obj
    
    elements = getattr(obj, "@elements", None) or getattr(obj, "elements", [])
    for element in elements or []:
        found = find_collection_by_name(element, collection_name)
        if found:
            return found
    
    return None


def flatten_layer_structure(data):
    """
    Remove the Layer 01 structure and move BrepX objects directly under the collection.
    Returns the flattened elements list.
    """
    elements = getattr(data, "@elements", None)
    if elements is None:
        elements = getattr(data, "elements", None)
    
    if not elements:
        return []
    
    flattened_elements = []
    
    for element in elements:
        # Check if this is the Layer 01 layer
        if getattr(element, "name", None) == "Layer 01":
            # Get the BrepX objects from inside Layer 01
            layer_elements = getattr(element, "@elements", None) or getattr(element, "elements", [])
            if layer_elements:
                flattened_elements.extend(layer_elements)
        else:
            # Keep other elements as is
            flattened_elements.append(element)
    
    return flattened_elements


def add_names_to_breps(elements):
    """
    Placeholder function - properties are now updated in STEP 1 via update_all_breps.
    This function is kept for backward compatibility with process_collection_recursively.
    """
    pass


def process_collection_recursively(element):
    """
    Recursively process collections to add names to BrepX objects.
    """
    if isinstance(element, Base):
        elements = getattr(element, "@elements", None) or getattr(element, "elements", [])
        if elements:
            add_names_to_breps(elements)
            
            for nested_element in elements:
                process_collection_recursively(nested_element)


# ============================================================================
# STEP 5: MAIN FUNCTION - PUTTING IT ALL TOGETHER
# ============================================================================

def main():
    print(f"\n{'='*70}")
    print(f"SPECKLE MODEL ORGANIZATION & DUPLICATION SCRIPT")
    print(f"{'='*70}\n")
    
    # Authenticate
    client = get_client()
    
    # Get the first version (the original with 2 objects)
    versions = client.version.get_versions(MODEL_ID, PROJECT_ID, limit=100)
    if not versions.items:
        print(" No versions found.")
        return
    
    first_version = versions.items[-1]  # Get the oldest version
    print(f" Fetching first version: {first_version.id}\n")
    
    # Receive the full data tree
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(first_version.referenced_object, transport)
    
    # ========================================================================
    # STEP 5.1: FIND AND DUPLICATE THE TARGET OBJECT
    # ========================================================================
    print(f"{'='*70}")
    print(f"STEP 1: Find and Update Original Objects + Duplicate Target")
    print(f"{'='*70}")
    
    target_obj = find_object_by_application_id(data, TARGET_APPLICATION_ID)
    
    if not target_obj:
        print(f" Could not find object with applicationId: {TARGET_APPLICATION_ID}")
        return
    
    print(f"  Found target object!")
    print(f"  Original Module: {getattr(getattr(target_obj, 'properties', None), 'Module', 'N/A')}")
    print(f"  Original Designer: {getattr(getattr(target_obj, 'properties', None), 'Designer', 'N/A')}")
    
    # Find ALL BrepX objects and update their properties based on Module
    print(f"\n Updating properties for all BrepX objects...")
    def update_all_breps(obj):
        """Recursively find and update all BrepX objects"""
        speckle_type = getattr(obj, "speckle_type", "")
        if "BrepX" in speckle_type or "Objects.Geometry" in speckle_type:
            properties = getattr(obj, "properties", None)
            if properties:
                if isinstance(properties, dict):
                    module = properties.get("Module")
                    if module in OLD_NESTED_PROPERTIES:
                        config = OLD_NESTED_PROPERTIES[module]
                        properties["Designer"] = config["Designer"]
                        obj["properties"] = properties
                        print(f"  OK Updated Module {module} -> Designer: {config['Designer']}")
        
        # Recursively check nested elements
        elements = getattr(obj, "@elements", None) or getattr(obj, "elements", None)
        if elements:
            for element in elements:
                update_all_breps(element)
    
    update_all_breps(data)
    
    # Create duplicated object with new properties
    print(f"\n Creating duplicate with:")
    print(f"  • Z offset: {OFFSET_Z} mm")
    print(f"  • Module: {NEW_NESTED_PROPERTIES.get('Module')}")
    print(f"  • Designer: {NEW_NESTED_PROPERTIES.get('Designer')}")
    
    copied_obj = deep_copy_and_offset(
        target_obj, 
        OFFSET_Z,
        nested_props=NEW_NESTED_PROPERTIES
    )
    
    print(f" Created duplicate successfully!\n")
    
    # ========================================================================
    # STEP 5.2: CREATE NEW COLLECTION FOR DUPLICATED OBJECT
    # ========================================================================
    print(f"{'='*70}")
    print(f"STEP 2: Create 'New Modules' Collection")
    print(f"{'='*70}")
    
    new_collection = Base()
    new_collection.speckle_type = "Speckle.Core.Models.Collection"
    new_collection._speckle_type = "Speckle.Core.Models.Collection"
    new_collection["speckle_type"] = "Speckle.Core.Models.Collection"
    new_collection.name = "New Modules"
    new_collection.elements = [copied_obj]
    
    print(f" Created 'New Modules' collection")
    print(f" Added duplicated object to collection\n")

    # ========================================================================
    # STEP 5.2B: PREP ROOT AS 'SPECKLEPY'
    # ========================================================================
    print(f"{'='*70}")
    print(f"STEP 2B: Set root name to 'Specklepy'")
    print(f"{'='*70}")

    data.name = "Specklepy"
    print(f" Root collection renamed to 'Specklepy'\n")
    
    # ========================================================================
    # STEP 5.3: CREATE "OLD MODULES" COLLECTION UNDER ROOT
    # ========================================================================
    print(f"{'='*70}")
    print(f"STEP 3: Create 'Old Modules' Collection")
    print(f"{'='*70}")

    old_modules_collection = Base()
    old_modules_collection.speckle_type = "Speckle.Core.Models.Collection"
    old_modules_collection._speckle_type = "Speckle.Core.Models.Collection"
    old_modules_collection["speckle_type"] = "Speckle.Core.Models.Collection"
    old_modules_collection.name = "Old Modules"

    print(f" Created 'Old Modules' collection\n")
    
    # ========================================================================
    # STEP 5.4: FLATTEN STRUCTURE (REMOVE LAYER 01)
    # ========================================================================
    print(f"{'='*70}")
    print(f"STEP 4: Remove 'Layer 01' Structure")
    print(f"{'='*70}")
    
    elements = getattr(data, "@elements", None)
    if elements is None:
        elements = getattr(data, "elements", None)
    
    if elements:
        original_count = len(elements)
        old_modules_collection.elements = elements

        # Flatten Layer 01 inside Old Modules
        flattened_old_modules = flatten_layer_structure(old_modules_collection)
        old_modules_collection.elements = flattened_old_modules

        specklepy_elements = [old_modules_collection, new_collection]

        if hasattr(data, "@elements"):
            data["@elements"] = specklepy_elements
        else:
            data.elements = specklepy_elements

        print(f"Removed 'Layer 01' layer")
        print(f"BrepX objects now directly under 'Old Modules'")
        print(f"Wrapped Old/New modules in root 'Specklepy' collection")
        print(f"  Elements count: {original_count} -> {len(specklepy_elements)}\n")
    
    # ========================================================================
    # STEP 5.5: ADD NAMES TO ALL BREPX OBJECTS
    # ========================================================================
    print(f"{'='*70}")
    print(f"STEP 5: Add Names to BrepX Objects")
    print(f"{'='*70}")
    
    elements = getattr(data, "@elements", None)
    if elements is None:
        elements = getattr(data, "elements", None)
    
    if elements:
        for element in elements:
            process_collection_recursively(element)
    
    print()
    
    # ========================================================================
    # STEP 5.6: COMMIT TO SPECKLE
    # ========================================================================
    print(f"{'='*70}")
    print(f"STEP 6: Commit to Speckle")
    print(f"{'='*70}")
    
    object_id = operations.send(data, [transport])
    print(f"OK Sent object: {object_id}")
    
    # Create a new version
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput
    
    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=MODEL_ID,
        objectId=object_id,
        message=f"Complete: Duplicated object (offset {OFFSET_Z}mm), organized structure with Old_Modules and New_Modules"
    ))
    
    print(f"OK Created version: {version.id}")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print(f"\n{'='*70}")
    print(f"OK SUCCESS! MODEL UPDATED")
    print(f"{'='*70}")
    print(f"Changes applied:")
    print(f"     Collections:")
    print(f"     'Unnamed document' -> 'Old Modules'")
    print(f"      Created 'New Modules' collection")
    print(f"      Wrapped in 'Specklepy' collection")
    print(f"    Structure:")
    print(f"      Removed 'Layer 01' nesting")
    print(f"      Flattened BrepX objects")
    print(f"   Objects:")
    print(f"      Module 01 -> (Designer: Rania Chihaoui)")
    print(f"      Module 03 -> (Designer: Eleni Maglari)")
    print(f"      Module 02 -> (Designer: Eduardo Martinez, offset {OFFSET_Z}mm)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
