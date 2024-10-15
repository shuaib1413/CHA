import os
from typing import List
from typing import Tuple

from datapipes import DatapipeType
from interface import Interface
from llms import LLMType
from orchestrator import Orchestrator
from planners import Action
from planners import PlannerType
from pydantic import BaseModel
from response_generators import (
    ResponseGeneratorType,
)
from tasks import TASK_TO_CLASS
from tasks import TaskType
from utils import parse_addresses


class CHA(BaseModel):
    name: str = "CHA"
    previous_actions: List[Action] = []
    orchestrator: Orchestrator = None
    planner_llm: str = LLMType.OPENAI
    planner: str = PlannerType.TREE_OF_THOUGHT
    datapipe: str = DatapipeType.MEMORY
    promptist: str = ""
    response_generator_llm: str = LLMType.OPENAI
    response_generator: str = ResponseGeneratorType.BASE_GENERATOR
    meta: List[str] = []
    verbose: bool = False

    def _generate_history(
        self, chat_history: List[Tuple[str, str]] = None
    ) -> str:
        if chat_history is None:
            chat_history = []

        history = "".join(
            [
                f"\n------------\nUser: {chat[0]}\nCHA: {chat[1]}\n------------\n"
                for chat in chat_history
            ]
        )
        return history

    def _run(
        self,
        query: str,
        chat_history: List[Tuple[str, str]] = None,
        tasks_list: List[str] = None,
        use_history: bool = False,
        **kwargs,
    ) -> str:
        if chat_history is None:
            chat_history = []
        if tasks_list is None:
            tasks_list = []

        history = self._generate_history(chat_history=chat_history)
        # query += f"User: {message}"
        # print(orchestrator.run("what is the name of the girlfriend of Leonardo Dicaperio?"))

        if self.orchestrator is None:
            self.orchestrator = Orchestrator.initialize(
                planner_llm=self.planner_llm,
                planner_name=self.planner,
                datapipe_name=self.datapipe,
                promptist_name=self.promptist,
                response_generator_llm=self.response_generator_llm,
                response_generator_name=self.response_generator,
                available_tasks=tasks_list,
                previous_actions=self.previous_actions,
                verbose=self.verbose,
                **kwargs,
            )

        response = self.orchestrator.run(
            query=query,
            meta=self.meta,
            history=history,
            use_history=use_history,
            **kwargs,
        )

        return response

    def respond(
        self,
        message,
        openai_api_key_input,
        serp_api_key_input,
        chat_history,
        check_box,
        tasks_list,
    ):
        os.environ["OPENAI_API_KEY"] = openai_api_key_input
        os.environ["SEPR_API_KEY"] = serp_api_key_input
        response = self._run(
            query=message,
            chat_history=chat_history,
            tasks_list=tasks_list,
            use_history=check_box,
        )

        files = parse_addresses(response)

        if len(files) == 0:
            chat_history.append((message, response))
        else:
            for i in range(len(files)):
                chat_history.append(
                    (
                        message if i == 0 else None,
                        response[: files[i][1]],
                    )
                )
                chat_history.append((None, (files[i][0],)))
                response = response[files[i][2] :]

        return "", chat_history

    def reset(self):
        self.previous_actions = []

    def run_with_interface(self):
        available_tasks = [key.value for key in TASK_TO_CLASS.keys()]
        interface = Interface()
        interface.prepare_interface(
            respond=self.respond,
            reset=self.reset,
            upload_meta=self.upload_meta,
            available_tasks=available_tasks,
        )

    def upload_meta(self, history, file):
        history = history + [((file.name,), None)]
        self.meta.append(file.name)
        return history

    def run(
        self,
        query: str,
        chat_history: List[Tuple[str, str]] = None,
        available_tasks: List[str] = None,
        use_history: bool = False,
        **kwargs,
    ) -> str:
        if chat_history is None:
            chat_history = []
        if available_tasks is None:
            available_tasks = []

        return self._run(
            query=query,
            chat_history=chat_history,
            tasks_list=available_tasks,
            use_history=use_history,
            **kwargs,
        )
