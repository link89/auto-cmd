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

### Prepare
Please ensure you having Python >=3.6 installed.

For Windows user, you may need to install `Microsoft C++ Build Tool`.

You should ensure Tesseract is installed in your system. Both version 4 and 5 are supported.
For Windows user this would be a little tedious, you have to add its path to environment variable.
Run the following command to test if tesseract is installed correctly.
```shell
tesseract -v
```

### Installation

```shell
pip install -U pip  # upgrade pip to avoid unexpected issue
pip install https://github.com/link89/auto-cmd/archive/refs/heads/main.zip
```
Run the following command to test if everything is OK.
It may take several seconds to finish, don't touch your mouse and keyboard before it finish.

```shell
auto-cmd open_browser 'https://github.com/link89/auto-cmd' - sleep 5 - take_screenshot - grayscale - bi_level 0 128 - ocr - find star - move_to - click
```

### Commands
TBD
