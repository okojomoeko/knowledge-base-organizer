"""Test main.py for check method in main class and todo app."""

from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock

import pytest
from pytest_mock import MockFixture

from knowledge_base_organizer.main import BaseClass, MyClass


@pytest.fixture
def my_class_instance() -> MyClass:
    """my_class fixture.

    Returns:
        MyClass: An instance of MyClass.
    """
    return MyClass()


def test_method(my_class_instance: MyClass) -> None:
    """Test MyClass.method()."""
    assert my_class_instance.method() == "Hello"


def test_class_method_is_not_implemented() -> None:
    """Test MyClass.class_method()."""
    assert BaseClass.class_method() is None


def test_class_method(my_class_instance: MyClass) -> None:
    """Test MyClass.class_method()."""
    assert my_class_instance.class_method() == "World"


def test_my_method() -> None:
    """Test MyClass.my_method()."""
    expect = 3
    assert MyClass.my_method(1, 2) == expect


@pytest.fixture
def mock_inputs(mocker: MockFixture) -> MagicMock | AsyncMock | NonCallableMagicMock:
    """Mock input().

    Returns:
        MagicMock: Mock of builtins.input()
    """
    return mocker.patch("builtins.input")


@pytest.mark.parametrize(
    ("select_num", "expected"),
    [(["1", "taskname", "taskdesc", "2", "5"], None), ("5", None)],
)
def test_main(
    mock_inputs: MagicMock,
    select_num: str,
    expected: object | None,
) -> None:
    """Test main todo sample application behavior.

    Args:
        mock_inputs (MagicMock): input() mock
        select_num (str): Select todo app option
        expected (object | None): _description_
    """
    mock_inputs.side_effect = select_num
    assert MyClass.main() == expected
