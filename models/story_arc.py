from pydantic import BaseModel, Field
from typing import List, Dict, Any

class PlotPoint(BaseModel):
    id: str = Field(description="A unique identifier for this plot point, e.g., '1_FindTheMap'.")
    title: str = Field(description="A short title for the plot point.")
    description: str = Field(description="A description of the goal for this part of the story.")
    completion_conditions: str = Field(description="A natural language description of what needs to happen for this plot point to be considered complete.")

class StoryArc(BaseModel):
    title: str = Field(description="The overall title of the campaign.")
    main_goal: str = Field(description="The ultimate objective of the story.")
    starting_location: str = Field(description="The name of the location where the campaign begins.")
    initial_character_prompt: str = Field(description="A detailed prompt to generate the initial NPC or situation the players encounter.")
    plot_points: List[PlotPoint] = Field(description="An ordered list of the key plot points that make up the story.")
    current_plot_point_id: str = Field(description="The ID of the currently active plot point.")
    persistent_world_state: Dict[str, Any] = Field(default_factory=dict, description="A dictionary to store major world events that persist across scenes, e.g., {'CityDestroyed': True}.")
