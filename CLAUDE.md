# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Test Commands
- Run the main application: `python main.py`
- Run raw device monitor: `python device.py`
- Install dependencies: `pip install -r requirements.txt` 
- Run tests: `pytest`
- Run single test: `pytest tests/test_file.py::test_function`
- Lint: `flake8 .`
- Type check: `mypy .`

## Code Style Guidelines
- **Imports**: Standard library first, third-party second, local modules last
- **Formatting**: Follow PEP 8 conventions, 4 spaces indentation
- **Type Hints**: Use for all function definitions, return types, and variables
- **Naming**: 
  - snake_case for functions, variables, and modules
  - CamelCase for classes
  - ALL_CAPS for constants
- **Error Handling**: Use try/except blocks with specific exceptions
- **Documentation**: Docstrings for all public functions, classes, and modules
- **Testing**: Write unit tests for all functionality

## Project Structure
This is a fencing scoring system that processes data from VSM HID devices. It:
- Monitors fencing hit states between two players
- Manages player health points and scoring
- Displays a GUI with health bars and status information
- Allows configuration of damage values and game parameters

