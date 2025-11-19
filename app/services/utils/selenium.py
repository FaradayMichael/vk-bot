import logging
import time
from urllib.parse import quote

from selenium.webdriver.common.by import By
from seleniumbase import SB

from app.schemas.images import ImageTags
from app.utils.config import Config

logger = logging.getLogger(__name__)


class SeleniumHelper:

    def __init__(self, config: Config):
        self._config = config

        self.__base_search_url = "https://yandex.ru/images/search?rpt=imageview&url="
        self._sb_params = dict(
            uc=True,
            test=True,
            ad_block=True,
            locale_code="ru",
            headed=True,
            xvfb=False,  # Xvfb уже запущен в start.sh
            headless=False,  # Возможно лишнее
            # proxy=proxy.dsn if proxy else None,
        )
        self._timeout = 3

    def get_image_tags(self, image_url: str) -> ImageTags:
        tags = []
        description = None
        text = None
        products_data = []

        search_url = self._get_search_url(image_url)
        logger.info(search_url)

        with SB(**self._sb_params) as driver:
            driver.uc_open_with_reconnect(search_url, reconnect_time=2)
            time.sleep(2)

            # driver.save_screenshot('1.png')

            try:
                more_btn_element = driver.find_element(
                    By.CSS_SELECTOR,
                    "//button[contains(@aria-label, 'Показать ещё')]",
                    timeout=self._timeout,
                )
                if more_btn_element:
                    more_btn_element.click()
                time.sleep(0.5)
            except Exception as e:
                logger.error(e)

            # tags
            try:
                elements = driver.find_elements(
                    By.XPATH, "//a[contains(@href, '/images/search?text=')]"
                )
                for element in elements:
                    tags.append(element.text)
            except Exception as e:
                logger.error(e)

            # description
            try:
                description_element = driver.find_element(
                    By.CLASS_NAME,
                    "CbirObjectResponse-Description",
                    timeout=self._timeout,
                )
                logger.info(description_element)
                description = description_element.text
            except Exception as e:
                logger.error(e)

            # text
            try:
                text_elements = driver.find_elements(
                    By.CSS_SELECTOR, "//div[contains(@class, 'CbirOcr-TextBox')]"
                )
                logger.info(f"{text_elements=}")
                text = " ".join([i.text for i in text_elements])
            except Exception as e:
                logger.error(e)

            # products
            try:
                products_elements = driver.find_elements(
                    By.CSS_SELECTOR,
                    "//a[contains(@class, 'Link EProductSnippetTitle')]",
                )
                for element in products_elements:
                    if href := element.get_attribute("href"):
                        products_data.append(href)
            except Exception as e:
                logger.exception(e)

        return ImageTags(
            tags=tags,
            description=description,
            text_on_image=text,
            products_data=products_data,
        )

    def _get_search_url(self, base_link: str) -> str:
        return self.__base_search_url + quote(base_link)
