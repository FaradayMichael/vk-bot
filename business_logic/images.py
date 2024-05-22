import asyncio
import logging
from urllib.parse import (
    quote,
    urljoin,
    unquote
)

import aiohttp
from bs4 import BeautifulSoup

from models.images import ImageTags

logger = logging.getLogger(__name__)


async def parse_image_tags(
        image_link: str,
        tries: int = 3
) -> ImageTags:
    match_str = "https://yandex.ru/images/search?text="
    base_search_url = "https://yandex.ru/images/search?rpt=imageview&url="

    search_url = base_search_url + quote(image_link)
    logger.info(search_url)

    result = ImageTags()
    for i in range(tries):
        if i > 0:
            logger.info(f'try: {i + 1}')
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as resp:
                if not resp.status == 200:
                    logger.info(await resp.text())
                    await asyncio.sleep(5)
                    continue
                soup = BeautifulSoup(await resp.read(), features="html5lib")
        await asyncio.sleep(0)

        links = soup('a')
        if "captcha" in " ".join(str(x) for x in links):
            logger.info("Captcha!")
            await asyncio.sleep(5)
            continue

        for link in links:
            if 'href' in dict(link.attrs):
                url = urljoin(search_url, link['href'])
                if url.find("'") != -1:
                    continue
                url = url.split('#')[0]
                if match_str in url:
                    result.tags.append(
                        unquote(url.replace(match_str, ''))
                    )

        desc = soup.find('div', {"class": "CbirObjectResponse-Description"})
        if desc:
            result.description = desc.text

        products = soup.find_all("li", {"class": "CbirMarketProducts-Item CbirMarketProducts-Item_type_product"})
        if products:
            for p in products:
                price = p.find('span', {"class": "Price-Value"}).get_text()
                link = p.find('a').get('href', None)
                if "http" not in link:
                    if "market.yandex" in link:
                        link = f"https:{link}"
                    elif "products/product" in link:
                        link = f"https://yandex.ru{link}"
                    else:
                        continue
                if price and link:
                    result.products_data.append(
                        f"{price} - {link}"
                    )

        if result.tags:
            break
        await asyncio.sleep(3)

    return result
