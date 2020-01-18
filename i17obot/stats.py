import asyncio
import itertools
from collections import Counter
from pprint import pprint

from transifex import transifex_api, strings_from_resource


async def get_all_strings():
    resources = await transifex_api(f"resources/")
    print("Resources found:", len(resources))

    semaphore = asyncio.Semaphore(1)
    async with semaphore:
        strings = await asyncio.gather(
            *[strings_from_resource(resource["slug"]) for resource in resources]
        )

    print("Strings found:", len(strings))
    return list(itertools.chain.from_iterable(strings))


async def users_with_transations():
    strings = await get_all_strings()
    users = []
    for string in strings:
        if user := string.get("user"):
            users.append(user)

    pprint(Counter(users))


if __name__ == "__main__":
    asyncio.run(users_with_transations())
