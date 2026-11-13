import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from repository import PredictionRepository
from service import ModerationService


class AdRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)

    seller_id: int = Field(gt=0)
    is_verified_seller: bool
    item_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: int = Field(gt=0)
    images_qty: int = Field(ge=0)


app = FastAPI(title="Модерация объявлений")
service = ModerationService(PredictionRepository())
logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(map(str, error["loc"][1:])), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": errors})


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Prediction failed", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post(
    "/predict",
    response_model=bool,
    summary="Есть ли в объявлении нарушение",
    responses={400: {"description": "Некорректные данные"}, 500: {"description": "Внутренняя ошибка"}},
)
def predict(ad: AdRequest) -> bool:
    return service.predict(ad.item_id, ad.is_verified_seller, ad.images_qty)


# Валидация в этом API возвращает 400, поэтому убираем стандартный 422 из документации.
app.openapi()["paths"]["/predict"]["post"]["responses"].pop("422", None)
