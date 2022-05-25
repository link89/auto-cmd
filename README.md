# auto-cmd
Cross platforms and cross languages desktop automation solution.

## Introduction

### Goals
* Run desktop operation without writing code.
* Language and platform agnostic.
* Compose multiple operation in single line.
* Remote execution via HTTP protocol.
* Easy to add customize commands/features.

### Tech Solutions
* Provide command line and HTTP interface with `python-fire`.
* Provide HTTP service with `FastAPI`.
* Chain multiple commands in a single call.

### Features
* Locate UI element via system interface, OCR and image matching.
* Image process.


## Get started

### Prepare
#### Python
Please ensure you have Python >=3.6 installed.

For Windows user, you may need to install `Microsoft C++ Build Tool`.

#### Tesseract
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
auto-cmd open_browser https://github.com/link89/auto-cmd - sleep 5 - take_screenshot - grayscale - bi_level 0 128 - tesseract - find star - move_to - click
```
To test the remote execution via HTTP, you should start the HTTP server first
```shell
auto-cmd-http
```
By default, this command will start an HTTP server listen on `localhost:5000`.
If you want to allow remote access or change the port, please use the following command.

```shell
auto-cmd-http --host 0.0.0.0 --port 5001
```
Now in your browser you can access the Swagger document via http://localhost:5000/docs
Click Try it out and copy arguments of the previous command to the request body, like below.
```json
{
  "args": "open_browser https://github.com/link89/auto-cmd - sleep 5 - take_screenshot - grayscale - bi_level 0 128 - tesseract - find star - move_to - click"
}
```
Then click Execute, you will find the command start to execute on the remote machine.

## Commands
TBD

## Integrate with `selenium-federation`
TBD

## Developers Guide
TBD