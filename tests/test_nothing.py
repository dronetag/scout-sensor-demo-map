from typing import Generator
import pytest

# to test your app- use absolute imports just like any third-party package
# import your-app.module

# use `print` to log in tests because only those will get printed out on test failure


@pytest.fixture
def name_matters() -> Generator[int, None, None]:
    print("Entering fixture")
    yield 1
    print("Exiting fixture")


def test_nothing(name_matters: int):
    print("Entering test")
    assert name_matters == 1, "fixture failed"
    print("Exiting test")
