"""
Scraper for bazar.bg website
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from sources.scrapers.base_scraper import BaseScraper
from sources.utils.logger import get_logger

logger = get_logger("bazar_bg_scraper")


class BazarBGScraper(BaseScraper):
    """
    Scraper for bazar.bg website
    Handles clicking buttons to reveal phone numbers and navigate image galleries
    """

    def __init__(self, headless: bool = False):
        """
        Initialize scraper for bazar.bg

        Args:
            headless: Run browser in headless mode
        """
        super().__init__(headless=headless)

    def click_phone_button(self) -> bool:
        """
        Click the phone button to reveal seller's phone number.

        Returns:
            bool: True if button was clicked successfully
        """
        try:
            # Wait for phone button to be present
            phone_button = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.adConnectButtonPhone'))
            )

            # Check if button is clickable
            if phone_button.is_displayed():
                phone_button.click()
                logger.info("Phone button clicked")
                time.sleep(0.5)  # Wait for any dynamic content
                return True
            else:
                logger.warning("Phone button not visible")
                return False

        except Exception as e:
            logger.debug(f"Could not click phone button: {e}")
            return False

    def get_all_product_images(self) -> list:
        """
        Navigate through all product images by clicking next button.
        Collects all image URLs from the gallery.

        Returns:
            list: List of image URLs
        """
        images = []

        try:
            # Get initial image count from dots
            dots = self.driver.find_elements(By.CSS_SELECTOR, '.imageDots a')
            total_images = len(dots)

            if total_images == 0:
                logger.debug("No image navigation dots found")
                return images

            logger.info(f"Found {total_images} images in gallery")

            # Collect all images by clicking through
            for i in range(total_images):
                # Get current active image
                active_img = self.driver.find_element(By.CSS_SELECTOR, 'span.gallery-element.active img.picture')
                img_src = active_img.get_attribute('src')

                if img_src and img_src.startswith('//'):
                    img_src = 'https:' + img_src

                if img_src and img_src not in images:
                    images.append(img_src)
                    logger.debug(f"Collected image {i+1}/{total_images}: {img_src}")

                # Click next button if not on last image
                if i < total_images - 1:
                    try:
                        next_button = self.driver.find_element(By.ID, 'nextImage')
                        next_button.click()
                        time.sleep(0.3)  # Wait for image transition
                    except Exception as e:
                        logger.warning(f"Could not click next image button: {e}")
                        break

            logger.info(f"Collected {len(images)} images total")
            return images

        except Exception as e:
            logger.error(f"Error getting product images: {e}")
            return images

    def scrape_product_page(self, url: str, click_phone: bool = True, get_images: bool = True) -> str:
        """
        Load product page and optionally interact with it (click phone, navigate images).

        Args:
            url: Product URL
            click_phone: Whether to click phone button to reveal number
            get_images: Whether to navigate through image gallery

        Returns:
            str: HTML content of the page after interactions
        """
        if not self.get_page(url, timeout=15):
            logger.error(f"Failed to load product page: {url}")
            return ""

        # Wait for main content to load
        time.sleep(2)

        # Click phone button if requested
        if click_phone:
            self.click_phone_button()

        # Navigate images if requested
        if get_images:
            self.get_all_product_images()

        return self.get_page_html()
