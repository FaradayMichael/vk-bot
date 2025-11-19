import asyncio
import logging
import uuid
from pathlib import Path
from urllib.parse import quote, urljoin, unquote

import aiohttp
from bs4 import BeautifulSoup
from PIL import Image, ImageFont, ImageDraw

from app.schemas.images import ImageTags

logger = logging.getLogger(__name__)


BASE_SEARCH_URL = "https://yandex.ru/images/search?rpt=imageview&url="


def get_search_url(base_link: str) -> str:
    return BASE_SEARCH_URL + quote(base_link)


async def parse_image_tags(image_link: str, tries: int = 3) -> ImageTags:
    match_str = "https://yandex.ru/images/search?text="

    search_url = get_search_url(image_link)
    logger.info(search_url)

    result = ImageTags()
    for i in range(tries):
        if i > 0:
            logger.info(f"try: {i + 1}")
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as resp:
                if not resp.status == 200:
                    logger.info(await resp.text())
                    await asyncio.sleep(5)
                    continue
                soup = BeautifulSoup(await resp.read(), features="html5lib")
        await asyncio.sleep(0)

        links = soup("a")
        if "captcha" in " ".join(str(x) for x in links):
            logger.info("Captcha!")
            await asyncio.sleep(5)
            continue

        for link in links:
            if "href" in dict(link.attrs):
                url = urljoin(search_url, link["href"])
                if url.find("'") != -1:
                    continue
                url = url.split("#")[0]
                if match_str in url:
                    result.tags.append(unquote(url.replace(match_str, "")))

        desc = soup.find("div", {"class": "CbirObjectResponse-Description"})
        if desc:
            result.description = desc.text
            desc_src = soup.find(
                "a",
                {"class": "Link Link_view_quaternary CbirObjectResponse-SourceLink"},
            )
            if desc_src:
                href = desc_src.get("href", None)
                if href is not None:
                    result.description += "\n" + quote(href, safe="/:")

        products = soup.find_all(
            "li",
            {"class": "CbirMarketProducts-Item CbirMarketProducts-Item_type_product"},
        )
        if products:
            for p in products:
                price = p.find("span", {"class": "Price-Value"}).get_text()
                link = p.find("a").get("href", None)
                if "http" not in link:
                    if "market.yandex" in link:
                        link = f"https:{link}"
                    elif "products/product" in link:
                        link = f"https://yandex.ru{link}"
                    else:
                        continue
                if price and link:
                    result.products_data.append(f"{price} - {link}")

        if result.tags:
            break
        await asyncio.sleep(3)

    return result


def add_text_to_image(
    filepath: str | Path,
    text: str,
    font: str | Path,
    font_size: int,
    font_color_rgb: tuple[int, int, int] = (0, 0, 0),
    text_xy_abs: tuple[int, int] | None = None,
    text_xy_rel: tuple[float, float] | None = None,
    to_sizes: tuple[int, int] | None = None,
    save_to: str | Path | None = None,
) -> str | Path:
    if text_xy_abs is None and text_xy_rel is None:
        raise TypeError("text_xy_abs or text_xy_rel must be specified")

    image = Image.open(filepath)
    if to_sizes:
        image.resize(size=to_sizes)
    image_w, image_h = image.size

    font_pil = ImageFont.truetype(font, font_size)
    draw = ImageDraw.Draw(image)
    _, _, text_w, text_h = draw.textbbox((0, 0), text, font=font_pil)

    if text_xy_abs:
        text_x = text_xy_abs[0] - text_w // 2
        text_y = text_xy_abs[1] - text_h // 2
    else:
        text_x = image_w * text_xy_rel[0] - text_w // 2
        text_y = image_h * text_xy_rel[1] - text_h // 2

    draw.text((text_x, text_y), text, font_color_rgb, font_pil)

    filename = f"{uuid.uuid4().hex}.jpg" if save_to is None else save_to
    image.save(filename)
    return filename
