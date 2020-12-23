import uvicorn
import logging
import uuid
import asyncio
import datetime as dt

import config
import models

from pathlib import Path
from steam_auth import SteamSignIn
from server import Server
from bots_controller import BotsController

from fastapi import FastAPI, Request, Depends, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from aiohttp_socks import ProxyError
from motor.motor_asyncio import AsyncIOMotorClient

directory = Path(__file__).parent

logging.basicConfig(
    filename=str((directory.parent / "logs.log").resolve()),
    level=logging.ERROR,
    format=f"%(asctime)s - %(levelname)s: %(message)s",
)

app = FastAPI()
app.mount("/static", StaticFiles(directory=directory.parent / "static"), name="static")
templates = Jinja2Templates(directory=directory / "templates")

loop = asyncio.get_event_loop()
mongo = AsyncIOMotorClient(
    config.MONGODB_HOST,
    config.MONGODB_PORT,
    io_loop=loop
)
database = mongo[config.MONGODB_NAME]
bots_controller = BotsController(database=database)


async def check_steam_auth(request: Request):
    steam_auth_guid = request.cookies.get("steam_auth_guid")

    if steam_auth_guid is None:
        return None, None

    steam_id_doc = await database.steam_auth.find_one({
        "auth_guid": steam_auth_guid
    })

    if steam_id_doc is None:
        return None, None

    if steam_id_doc["steamid_64"] not in config.APP_ADMIN_STEAMIDS:
        return None, None

    return steam_auth_guid, steam_id_doc["steamid_64"]


async def start_bot_task(bot_data):
    try:
        return await bots_controller.start_bot(bot_data)
    except ProxyError as e:
        log_type = "proxy"
        response = f"{e.__class__.__name__} {str(e)}"
    except Exception as e:
        if "rsa" in str(e).lower():
            log_type = "proxy"
        else:
            log_type = "steam"

        response = f"{e.__class__.__name__} {str(e)}"

        if hasattr(e, "response") and e.response:
            response += f" {await e.response.text()}"

        if hasattr(e, "message") and e.message:
            response += f" {e.message}"

    await database.logs.insert_one({
        "date": dt.datetime.now(),
        "type": log_type,
        "login": bot_data["login"],
        "proxy": bot_data.get("proxy"),
        "request": "login",
        "response": response
    })


@app.get("/", name="home")
async def home(request: Request):
    auth_guid, steamid = await check_steam_auth(request)

    if not steamid:
        return RedirectResponse(request.url_for("login"))

    bot_docs = await database.bots.find({}).to_list(None)
    bots = []

    for doc in bot_docs:
        if "login" not in doc:
            continue

        if doc.get("state"):
            client = bots_controller.is_running(doc["login"])

            if client is None:
                loop.create_task(start_bot_task(doc))
                doc["state"] = False
            else:
                doc["state"] = client.is_connected

        bots.append({k: v for k, v in doc.items() if v is not None})

    return templates.TemplateResponse("home.html", {
        "request": request,
        "steamid": steamid,
        "auth_guid": auth_guid,
        "bots": bots,
        "logs": await database.logs.find({}).sort([("date", -1)]).limit(100).to_list(None)
    })


@app.post("/api/bot")
async def bot_post(request: Request, data: models.BotModel):
    if not await check_steam_auth(request):
        return Response(status_code=403)

    dict_data = {k: v for k, v in data.dict().items() if v is not None}
    state = dict_data.get("state")

    if state is not None:
        client = bots_controller.is_running(dict_data["login"])

        if state:
            if client is None:
                bot_data = await database.bots.find_one({"login": dict_data["login"]})

                if bot_data is not None:
                    loop.create_task(start_bot_task(bot_data))
        else:
            if client is not None:
                loop.create_task(client.close())
                bots_controller.running_bots.remove(client)

    await database.bots.update_one(
        {"login": data.login},
        {"$set": dict_data},
        upsert=True
    )


@app.delete("/api/bot")
async def bot_delete(request: Request, data: models.BotModel):
    if not await check_steam_auth(request):
        return Response(status_code=403)

    client = bots_controller.is_running(data.login)

    if client is not None:
        await client.close()
        bots_controller.running_bots.remove(client)

    await database.bots.delete_one({
        "login": data.login
    })


@app.get("/login")
async def login(request: Request, steam_signin: SteamSignIn = Depends(SteamSignIn)):
    url = steam_signin.construct_url(request.url_for("process_login"))
    return steam_signin.redirect_user(url)


@app.get("/process_login")
async def process_login(
    request: Request,
    steam_signin: SteamSignIn = Depends(SteamSignIn)
):
    steam_id = steam_signin.validate_results(request.query_params)
    response = RedirectResponse(request.url_for("home"))

    if not steam_id:
        return Response(status_code=HTTP_401_UNAUTHORIZED)

    auth_guid = request.cookies.get("steam_auth_guid")

    if auth_guid is None:
        auth_guid = str(uuid.uuid4())
        response.set_cookie(
            "steam_auth_guid",
            auth_guid,
            # expires=315360000,
            max_age=315360000
        )

    if steam_id not in config.APP_ADMIN_STEAMIDS:
        return Response(status_code=HTTP_401_UNAUTHORIZED)

    document = {
        "auth_guid": auth_guid,
        "steamid_64": steam_id
    }

    await database.steam_auth.update_one(
        document,
        {"$set": document},
        upsert=True
    )

    return response


server_config = uvicorn.Config(app, host=config.APP_HOST, port=config.APP_PORT)
server = Server(server_config)
server.run(loop=loop)
