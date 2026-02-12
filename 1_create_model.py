"""
01 - Create a Speckle Model

This script demonstrates how to create a new model in existing Speckle project

NOTE: Projects must belong to a workspace. You can find your workspace ID
in the Speckle web interface URL:# https://app.speckle.systems/settings/workspaces/macad-iaac/general
"""

from xml.parsers.expat import model
from main import get_client
from specklepy.core.api.inputs.model_inputs import CreateModelInput


# TODO: Replace with your workspace ID

PROJECT_ID = "128262a20c"
MODEL_NAME = "homework/session04/team_03.2"
# You can find it in the URL when you open your workspace in Speckle web:
# https://app.speckle.systems/settings/workspaces/macad-iaac/general



def main():
    # Authenticate
    client = get_client()

    # Create a new model in the existing project
    model = client.model.create (CreateModelInput(

        projectId=PROJECT_ID,
        name=MODEL_NAME,
        description="homework04",
    ))

    # Get the model details
    print(f"OK Created model: {model.id}")
    print(f"  Model name: {model.name}")
    print(f"  Description:  {model.description}")

if __name__ == "__main__":
    main()
