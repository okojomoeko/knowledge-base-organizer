"""main entry point."""

import abc

from knowledge_base_organizer.sub_module import submodule1


class BaseClass(abc.ABC):
    """Base class with abstract methods `method` and `class_method`.

    Attributes:
        None

    Methods:
        method: Abstract method that must be implemented by subclasses.
            Returns the string "Hello".
        class_method: Class method that must be implemented by subclasses.
            Returns the string "World".
    """

    @abc.abstractmethod
    def method(self) -> str:
        """Abstract method that must be implemented by subclasses.

        Raises:
            NotImplementedError: If not overridden in a subclass.
        """

    @classmethod
    @abc.abstractmethod
    def class_method(cls) -> str:
        """Class method that must be implemented by subclasses.

        Returns:
            str: The string "World".
        """


class MyClass(BaseClass):
    """Concrete class implementing the abstract methods of `BaseClass`.

    Attributes:
        None

    Methods:
        method: Overrides the base class's `method` to return "Hello".
        class_method: Overrides the base class's `class_method` to return "World".
        my_method: Adds two integers and returns their sum.
    """

    def method(self) -> str:
        """Overrides the base class's `method`.

        Returns:
            str: The string "Hello".
        """
        self.print_str = "Hello"
        return self.print_str

    @classmethod
    def class_method(cls) -> str:
        """Overrides the base class's `class_method`.

        Returns:
            str: The string "World".
        """
        return "World"

    @staticmethod
    def my_method(a: int, b: int) -> int:
        """Adds two integers and returns their sum.

        Args:
            a (int): The first integer to add.
            b (int): The second integer to add.

        Returns:
        int: The sum of `a` and `b`.
        """
        return a + b

    @staticmethod
    def main() -> None:
        """Run todo manager."""
        todo_manager = submodule1.TodoManager()
        app = submodule1.TodoApp(todo_manager)
        app.run()


if __name__ == "__main__":
    a = MyClass()
    print(a.method())
    MyClass.main()
