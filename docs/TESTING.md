# Running Tests

After installing all dependencies (including `dev` dependencies where `pytest` and plugins are declared), you can run all tests from the project root using the following command:

```bash
pytest
```

Pytest will automatically discover and run all test files whose names start with `test_`.

The repository includes a `pytest.ini` configuration file that specifies the test directory and relevant options (e.g., enabling `asyncio` mode for asynchronous tests).

### Example Output

When tests are executed, you will see output indicating progress and status:

```bash
test_example.py::test_function PASSED
...
```

All tests should pass and return a `PASSED` status.
