import asyncio
import logging
import random
from urllib.parse import quote, urljoin

import aiohttp
from async_lru import alru_cache
from decouple import config

TRANSIFEX_TOKEN = config("TRANSIFEX_TOKEN")
TRANSIFEX_API = "https://www.transifex.com/api/2/project/python-newest/"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


async def transifex_api(url, data=None, retrying=False):
    if retrying:
        logger.info("retrying url=%s", url)

    auth = aiohttp.BasicAuth(login="api", password=TRANSIFEX_TOKEN)
    async with aiohttp.ClientSession(auth=auth) as session:
        http_method = session.put if data else session.get
        args = {"json": data} if data else {}

        try:
            async with http_method(urljoin(TRANSIFEX_API, url), **args) as response:
                logger.info("url=%s, status_code=%s", url, response.status)
                return await response.json()

        except aiohttp.client_exceptions.ClientConnectorSSLError as e:
            logger.error("url=%s, error=%s", url, e)
            if not retrying:
                await asyncio.sleep(2)
                return await transifex_api(url, retrying=True)
            raise


async def random_resource():
    resources = await transifex_api(f"resources/")
    resources = [resource["slug"] for resource in resources]
    resources = filter(
        lambda r: r.split("--")[0] in ["bugs", "howto", "library"], resources
    )
    resource = random.choice(list(resources))
    logger.info("random_resource, resource=%s", resource)
    return resource


async def strings_from_resource(resource):
    strings = await transifex_api(
        f"resource/{resource}/translation/pt_BR/strings/?details"
    )
    logger.info(
        "getting strings from resource, resource=%s, strings_found=%s",
        resource,
        len(strings),
    )
    for string in strings:
        string["resource"] = resource

    return strings


async def random_string(resource=None, translated=None, reviewed=None, max_size=None):
    if not resource:
        resource = await random_resource()

    strings = await strings_from_resource(resource)

    if translated is not None:
        strings = filter(lambda s: bool(s["translation"]) == translated, strings)

    if reviewed is not None:
        strings = filter(lambda s: s["reviewed"] == reviewed, strings)

    if max_size is not None:
        strings = filter(lambda s: len(s["source_string"]) <= max_size, strings)

    strings = list(strings)
    if not strings:
        if max_size:
            max_size += 300

        return await random_string(
            translated=translated, reviewed=reviewed, max_size=max_size
        )

    return resource, random.choice(list(strings))


def transifex_string_url(resource, key):
    query_string = f"text:'{key[:20]}'"
    return (
        "https://www.transifex.com/"
        f"python-doc/python-newest/translate/#pt_BR/{resource}/1"
        f"?q={quote(query_string)}"
    )


async def translate_string(resource, string_hash, translation):
    await transifex_api(
        f"resource/{resource}/translation/pt_BR/string/{string_hash}/",
        data={"translation": translation},
    )
