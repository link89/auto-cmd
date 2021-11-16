from fire.core import Fire
from typing import Union
from fastapi import FastAPI, Response
from pydantic import BaseModel

from . import AutoCmd
from .core import AutoCmdError
from .utils import get_stacktrace_from_exception


class Command(BaseModel):
    args: Union[str, list]


app = FastAPI()


@app.post("/auto-cmd/", status_code=200)
def auto_cmd(command: Command, response: Response):
    try:
        ret = Fire(AutoCmd, command.args)
        return {
            'result': ret.to_data(),
        }
    except AutoCmdError as e:
        response.status_code = e.code
        return {
            'error': e.to_data(),
        }
    except (Exception, SystemExit) as e:
        response.status_code = 500
        return {
            'error': {
                'code': 500,
                'error': 'unknown error',
                'message': str(e),
                'stacktrace': get_stacktrace_from_exception(e),
            }
        }


def run_server(host="127.0.0.1", port=5000, log_level="info"):
    import uvicorn
    uvicorn.run("auto_cmd.http_server:app", host=host, port=port, log_level=log_level)


def main():
    Fire(run_server)


if __name__ == '__main__':
    main()
