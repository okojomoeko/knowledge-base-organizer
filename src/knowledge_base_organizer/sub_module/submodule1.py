"""submodule including todo manager sample class."""

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class Task(BaseModel):
    """Represents a task with attributes like name, description, and completion status."""

    name: str
    description: str
    completed: str = ""
    created_at: datetime = datetime.now()


class BaseTodoManager(ABC):
    """Base class for a todo manager with abstract methods.

    Attributes:
        None

    Methods:
        add_task: Abstract method to add a task.
        list_tasks: Abstract method to list all tasks.
        mark_complete: Abstract method to mark a task as complete.
        remove_task: Abstract method to remove a task.
    """

    @abstractmethod
    def add_task(self, task: Task) -> int:
        """Abstract method to add a task.

        Args:
            task (str): The task to be added.

        Return:
           int: The ID of the newly added task.
        """

    @abstractmethod
    def list_tasks(self) -> None:
        """Abstract method to list all tasks."""

    @abstractmethod
    def mark_complete(self, task_id: int) -> None:
        """Abstract method to mark a task as complete.

        Args:
            task_id (int): The ID of the task to be marked as completed.
        """

    @abstractmethod
    def remove_task(self, task_id: int) -> None:
        """Abstract method to remove a task.

        Args:
            task_id (int): The ID of the task to be removed.
        """


class TaskData(BaseModel):
    """Concrete implementation of a task data class.

    Attributes:
        id (int): The unique identifier for the task.
        task (Task): The task.
    """

    id: int
    task: Task


class TodoManager(BaseTodoManager):
    """Concrete implementation of a todo manager using a list to store tasks.

    Attributes:
        tasks (list): A list of tasks in the format [task_id, task_name].

    Methods:
        add_task: Adds a new task and returns its ID.
        list_tasks: Lists all tasks with their IDs.
        mark_complete: Marks a task as complete by setting completed to True.
        remove_task: Removes a task by removing it from the list.
    """

    def __init__(self) -> None:
        """Constructor.

        Initialize the todo manager with an empty list of tasks.
        """
        self.tasks: list[TaskData] = []

    def add_task(self, task: Task) -> int:
        """Adds a new task and returns its ID.

        Args:
            task (Task): The task to add.

        Returns:
            int: The ID of the newly added task.
        """
        task_id = 1 if self.tasks == [] else max([task.id for task in self.tasks]) + 1
        self.tasks.append(TaskData(id=task_id, task=task))
        return task_id

    def list_tasks(self) -> None:
        """Lists all tasks with their IDs."""
        if not self.tasks:
            print("No tasks found.")
            return
        print("\n=================")
        for task_data in self.tasks:
            print(f"{task_data.id}({task_data.task.completed}). {task_data.task.name}")
        print("=================\n")

    def mark_complete(self, task_id: int) -> None:
        """Marks a task as complete by setting completed to True."""
        for task_data in self.tasks:
            if task_data.id == task_id:
                task_data.task.completed = "Completed!"
                print(f"Completed: {task_data.id}")
                print(f"Task {task_id} marked as complete.")
                return
        print("Task not found.")

    def remove_task(self, task_id: int) -> None:
        """Removes a task by removing it from the list."""
        for task_data in self.tasks:
            if task_data.id == task_id:
                del self.tasks[self.tasks.index(task_data)]
                print(f"Task {task_id} removed.")
                return
        print("Task not found.")


class TodoApp:
    """Todo application using a TodoManager.

    Attributes:
        manager (BaseTodoManager): An instance of the TodoManager class.

    Methods:
        run: Runs the todo application.
    """

    def __init__(self, manager: TodoManager) -> None:
        """Constructor.

        Args:
            manager (TodoManager): _description_
        """
        self.manager = manager

    def run(self) -> None:
        """Represents a task with attributes for name, description, completion status, and creation timestamp."""
        while True:
            print("\nTodo Application Menu:")
            print("1. Add Task")
            print("2. List Tasks")
            print("3. Mark Task as Complete")
            print("4. Remove Task")
            print("5. Exit")

            choice = input("Enter your choice: ")

            if choice == "1":
                task_name = input("Enter the task: ")
                task_description = input("Enter the task description: ")
                self.manager.add_task(
                    Task(name=task_name, description=task_description)
                )
            elif choice == "2":
                self.manager.list_tasks()
            elif choice == "3":
                task_id = int(input("Enter the task ID to mark as complete: "))
                self.manager.mark_complete(task_id)
            elif choice == "4":
                task_id = int(input("Enter the task ID to remove: "))
                self.manager.remove_task(task_id)
            elif choice == "5":
                print("Exiting the Todo Application.")
                break
            else:
                print("Invalid choice. Please try again.")
