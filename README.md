# auto-cmd
Cross platforms and cross languages desktop automation solution.

## Introduction

### Goals
* Run desktop operation without writing source code.
* Language and platform agnostic.
* Compose multiple operation in single line.
* Remote execution via HTTP protocol.
* Easy to add customize commands/features.

### Tech Solution
* Provide command line and HTTP interface with `python-fire`.
* Provide HTTP service with `FastAPI`.
* Chain multiple commands in a single call.

### Features
* Locate UI element via system interface, OCR and image matching.

## Get started

### Installation
Please ensure your Python >=3.6 before you continue.
```shell
pip install -U pip  # upgrade pip to avoid unexpected issue
pip install https://github.com/link89/auto-cmd/archive/refs/heads/main.zip
```
Run the following command to Star this project as a test, thank you.
```shell
auto-cmd open_browser 'https://github.com/link89/auto-cmd' - sleep 5 - take_screenshot - ocr - find Star - move_to - click
```

### Commands
TBD
