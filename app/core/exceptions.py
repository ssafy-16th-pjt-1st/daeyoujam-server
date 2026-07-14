from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class NotFoundError(Exception):
    def __init__(self, message: str = "Resource not found") -> None:
        self.message = message


class ForbiddenError(Exception):
    def __init__(self, message: str = "Forbidden") -> None:
        self.message = message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(_: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Database error", "error": str(exc)})

