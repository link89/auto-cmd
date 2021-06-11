from fire.core import Fire
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel

from . import AutoCmd


class Command(BaseModel):
    args: Union[str, list]


app = FastAPI()


@app.post("/auto-cmd/")
def auto_cmd(command: Command):
    result = Fire(AutoCmd, command.args)
    print(result)
    return result


def run_server(host="127.0.0.1", port=5000, log_level="info"):
    import uvicorn
    uvicorn.run("auto_cmd.http_server:app", host=host, port=port, log_level=log_level)


def main():
    Fire(run_server)
