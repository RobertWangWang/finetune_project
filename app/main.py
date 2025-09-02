import asyncio
import logging
import threading

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from requests import Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dataset_api import project_api, file_api, ga_pair_api, tag_api, file_pair_api, question_api, dataset_api, \
    job_api, catalog_api, dataset_version_api
from app.api.llamafactory_api import finetune_config_api, finetune_job_api, \
    release_api
from app.api.common_api import machine_api, llm_api
from app.api.deploy_api import deploy_cluster_api
from app.api.middleware.middleware import i18n_middleware
from app.api.middleware.middleware import wrap_response_middleware
from app.db.init import init_db
from app.services.dataset_services.jobs.manager import start_job_manager
from app.services.llamafactory_services.finetune_job_service import watch_starting_jobs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logging.info("Starting init_db")
init_db()
logging.info("End init_db")

thread = threading.Thread(target=asyncio.run, args=(start_job_manager(),))
thread.start()

job_thread = threading.Thread(target=asyncio.run, args=(watch_starting_jobs(),))
job_thread.start()


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    title="dataset-finetune-api",
    generate_unique_id_function=custom_generate_unique_id,
)


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers_for_allow_origin,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None,
        },
    )


@app.exception_handler(Exception)
def http_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        headers=headers_for_allow_origin,
        content={
            "code": 500,
            "message": str(exc),
            "data": None,
        },
    )


app.middleware("http")(i18n_middleware)
app.middleware("http")(wrap_response_middleware)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 允许跨域
headers_for_allow_origin = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': '*',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Max-Age': '3600',
}

app.include_router(project_api.router, prefix="/v1")
app.include_router(file_api.router, prefix="/v1")
app.include_router(ga_pair_api.router, prefix="/v1")
app.include_router(tag_api.router, prefix="/v1")
app.include_router(file_pair_api.router, prefix="/v1")
app.include_router(question_api.router, prefix="/v1")
app.include_router(dataset_api.router, prefix="/v1")
app.include_router(job_api.router, prefix="/v1")
app.include_router(catalog_api.router, prefix="/v1")
app.include_router(machine_api.router, prefix="/v1")
app.include_router(llm_api.router, prefix="/v1")
app.include_router(dataset_version_api.router, prefix="/v1")
app.include_router(finetune_config_api.router, prefix="/v1")
app.include_router(finetune_job_api.router, prefix="/v1")
app.include_router(release_api.router, prefix="/v1")
app.include_router(deploy_cluster_api.router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    from fastapi.routing import APIRoute

    for route in app.routes:
        if isinstance(route, APIRoute):
            print(f"{','.join(route.methods):10} {route.path}")

    # 启动服务
    uvicorn.run(app, host="0.0.0.0",
                port=8000,
                log_level="info",
                timeout_keep_alive=120)
