import json
from models.story_arc import StoryArc, PlotPoint
from typing import Optional
from generator import ObjectGenerator
from prompter import Prompter
from models.reuqest_types import StoryProgressionCheck

class StoryManager:
    def __init__(self, story_file_path: str):
        with open(story_file_path, 'r', encoding='utf-8') as f:
            self.story: StoryArc = StoryArc.model_validate(json.load(f))
        self.generator = ObjectGenerator()
        self.prompter = Prompter()

    def get_current_plot_context(self) -> str:
        current_point = self.get_current_plot_point()
        if not current_point:
            return "The main story has concluded."
        
        return f"""
        <STORY_CONTEXT>
        The overarching goal of the campaign '{self.story.title}' is: {self.story.main_goal}.
        The current active chapter of the story is '{current_point.title}'.
        The objective for this chapter is: {current_point.description}.
        To advance the story, the players need to achieve this: {current_point.completion_conditions}.
        </STORY_CONTEXT>
        """

    def get_current_plot_point(self) -> Optional[PlotPoint]:
        return next((p for p in self.story.plot_points if p.id == self.story.current_plot_point_id), None)

    def advance_story(self, direction: int = 1):
        current_index = -1
        for i, point in enumerate(self.story.plot_points):
            if point.id == self.story.current_plot_point_id:
                current_index = i
                break
        
        new_index = current_index + direction
        if 0 <= new_index < len(self.story.plot_points):
            self.story.current_plot_point_id = self.story.plot_points[new_index].id
            print(f"Story moved to: {self.story.current_plot_point_id}")
            return self.get_current_plot_point()
        else:
            print("End or beginning of story arc reached.")
            return None

    def set_plot_point(self, plot_point_id: str):
        if any(p.id == plot_point_id for p in self.story.plot_points):
            self.story.current_plot_point_id = plot_point_id
            print(f"Story set to: {self.story.current_plot_point_id}")
            return self.get_current_plot_point()
        else:
            print(f"Plot point with id {plot_point_id} not found.")
            return None

    def check_and_advance(self, context: str):
        prompt = self.prompter.get_story_progression_prompt(self, context)
        if not prompt:
            return

        result: StoryProgressionCheck = self.generator.generate(
            pydantic_model=StoryProgressionCheck,
            prompt=prompt
        )

        print(f"Story progression check: {result.reasoning}")
        if result.conditions_met:
            self.advance_story()
