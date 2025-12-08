import requests
import os
from dotenv import load_dotenv
import json
import logging
from typing import Optional, Dict, Any
import time
from requests.exceptions import RequestException, Timeout, ConnectionError
from data_preprocessing.preprocessing_pipeline import pipeline_gur_eur_data

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('razom_api/razom_api.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

token = os.getenv('RAZOM_API_TOKEN')


class RazomAPIError(Exception):
    """Custom exception for Razom API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


def get_access_token(max_retries: int = 3, timeout: int = 30) -> str:
    """
    Get access token from Razom API with proper error handling and retries.
    
    Args:
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        
    Returns:
        str: Access token
        
    Raises:
        RazomAPIError: If API request fails
        ValueError: If required environment variables are missing
    """
    if not token:
        logger.error("RAZOM_API_TOKEN environment variable is not set")
        raise ValueError("RAZOM_API_TOKEN environment variable is required")
    
    url = "https://razom.master.shop/api/v1/login"
    headers = {
        "X-Api-Token": token,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    logger.info(f"Attempting to get access token from {url}")
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1}/{max_retries}")
            
            response = requests.post(
                url, 
                headers=headers, 
                timeout=timeout,
                verify=True  # Ensure SSL verification
            )
            
            logger.info(f"Response status code: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    
                    if 'access_token' not in response_data:
                        logger.error("Response missing 'access_token' field")
                        raise RazomAPIError(
                            "Invalid response format: missing access_token",
                            status_code=response.status_code,
                            response_data=response_data
                        )
                    
                    access_token = response_data['access_token']
                    logger.info("Successfully obtained access token")
                    return access_token
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise RazomAPIError(
                        f"Invalid JSON response: {e}",
                        status_code=response.status_code
                    )
            
            elif response.status_code == 401:
                logger.error("Authentication failed - invalid API token")
                raise RazomAPIError(
                    "Authentication failed: invalid API token",
                    status_code=response.status_code
                )
            
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded, retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise RazomAPIError(
                        "Rate limit exceeded",
                        status_code=response.status_code
                    )
            
            elif response.status_code >= 500:
                logger.warning(f"Server error {response.status_code}, retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise RazomAPIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code
                    )
            
            else:
                logger.error(f"Unexpected status code: {response.status_code}")
                raise RazomAPIError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code
                )
        
        except Timeout:
            logger.warning(f"Request timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise RazomAPIError("Request timeout after all retry attempts")
        
        except ConnectionError:
            logger.warning(f"Connection error on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise RazomAPIError("Connection error after all retry attempts")
        
        except RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt == max_retries - 1:
                raise RazomAPIError(f"Request failed: {e}")
        
        # Wait before retrying (except for the last attempt)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            logger.info(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    raise RazomAPIError("Failed to get access token after all retry attempts")


def get_catalog_page(
    page_num: int, 
    bearer_token: str, 
    segment: str, 
    lang: str = 'en', 
    max_retries: int = 3, 
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Get catalog page from Razom API with proper error handling and retries.
    
    Args:
        page_num: Page number to retrieve (1-based)
        bearer_token: Bearer token for authentication
        segment: Product segment ('eur' or 'gur')
        lang: Language code ('en' or 'ru')
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        
    Returns:
        Dict[str, Any]: Catalog page data
        
    Raises:
        RazomAPIError: If API request fails
        ValueError: If required parameters are invalid
    """
    # Parameter validation
    if not bearer_token or not bearer_token.strip():
        logger.error("Bearer token is required")
        raise ValueError("Bearer token cannot be empty")
    
    if page_num < 1:
        logger.error(f"Invalid page number: {page_num}")
        raise ValueError("Page number must be >= 1")
    
    if segment not in ['eur', 'gur']:
        logger.error(f"Invalid segment: {segment}")
        raise ValueError("Segment must be 'eur' or 'gur'")
    
    if lang not in ['en', 'ru']:
        logger.error(f"Invalid language: {lang}")
        raise ValueError("Language must be 'en' or 'ru'")
    
    url = "https://razom.master.shop/api/v1/catalog"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    data = {
        "segment": segment,
        "lang": lang,
        "page": page_num
    }
    
    logger.info(f"Requesting catalog page {page_num} for segment '{segment}' in language '{lang}'")
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1}/{max_retries}")
            
            response = requests.post(
                url, 
                headers=headers, 
                json=data,
                timeout=timeout,
                verify=True
            )
            
            logger.info(f"Response status code: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"Successfully retrieved catalog page {page_num}")
                    return response_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise RazomAPIError(
                        f"Invalid JSON response: {e}",
                        status_code=response.status_code
                    )
            
            elif response.status_code == 401:
                logger.error("Authentication failed - invalid bearer token")
                raise RazomAPIError(
                    "Authentication failed: invalid bearer token",
                    status_code=response.status_code
                )
            
            elif response.status_code == 400:
                logger.error("Bad request - invalid parameters")
                try:
                    error_data = response.json()
                    raise RazomAPIError(
                        "Bad request: invalid parameters",
                        status_code=response.status_code,
                        response_data=error_data
                    )
                except json.JSONDecodeError:
                    raise RazomAPIError(
                        "Bad request: invalid parameters",
                        status_code=response.status_code
                    )
            
            elif response.status_code == 404:
                logger.error(f"Catalog page {page_num} not found")
                raise RazomAPIError(
                    f"Catalog page {page_num} not found",
                    status_code=response.status_code
                )
            
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded, retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise RazomAPIError(
                        "Rate limit exceeded",
                        status_code=response.status_code
                    )
            
            elif response.status_code >= 500:
                logger.warning(f"Server error {response.status_code}, retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise RazomAPIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code
                    )
            
            else:
                logger.error(f"Unexpected status code: {response.status_code}")
                raise RazomAPIError(
                    f"API request failed with status {response.status_code}",
                    status_code=response.status_code
                )
        
        except Timeout:
            logger.warning(f"Request timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise RazomAPIError("Request timeout after all retry attempts")
        
        except ConnectionError:
            logger.warning(f"Connection error on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise RazomAPIError("Connection error after all retry attempts")
        
        except RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt == max_retries - 1:
                raise RazomAPIError(f"Request failed: {e}")
        
        # Wait before retrying (except for the last attempt)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            logger.info(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    raise RazomAPIError("Failed to get catalog page after all retry attempts")


def get_catalog_full(
    bearer_token: str, 
    segment: str, 
    lang: str = 'en',
    max_retries: int = 3,
    timeout: int = 30,
    delay_between_pages: float = 0.5
) -> Dict[str, Any]:
    """
    Get complete catalog from Razom API by fetching all pages with proper error handling.
    
    Args:
        bearer_token: Bearer token for authentication
        segment: Product segment ('eur' or 'gur')
        lang: Language code ('en' or 'ru')
        max_retries: Maximum number of retry attempts per page
        timeout: Request timeout in seconds per page
        delay_between_pages: Delay in seconds between page requests to avoid rate limiting
        
    Returns:
        Dict[str, Any]: Complete catalog data with merged results and final pagination info
        
    Raises:
        RazomAPIError: If API request fails
        ValueError: If required parameters are invalid
    """
    logger.info(f"Starting full catalog fetch for segment '{segment}' in language '{lang}'")
    
    # Get first page to understand pagination
    try:
        first_page = get_catalog_page(
            page_num=1, 
            bearer_token=bearer_token, 
            segment=segment, 
            lang=lang,
            max_retries=max_retries,
            timeout=timeout
        )
    except RazomAPIError as e:
        logger.error(f"Failed to fetch first catalog page: {e.message}")
        raise
    
    if not first_page.get('success', False):
        logger.error("First page response indicates failure")
        raise RazomAPIError("API returned success=false", response_data=first_page)
    
    # Extract pagination info
    pagination = first_page.get('pagination', {})
    total_pages = pagination.get('total_pages', 1)
    total_items = pagination.get('total', 0)
    
    logger.info(f"Found {total_pages} total pages with {total_items} total items")
    
    # Initialize result structure
    all_data = first_page.get('data', [])
    meta = first_page.get('meta', {})
    
    # If there's only one page, return immediately
    if total_pages <= 1:
        logger.info("Only one page available, returning first page data")
        return {
            'success': True,
            'data': all_data,
            'pagination': {
                'current_page': 1,
                'per_page': pagination.get('per_page', len(all_data)),
                'total': total_items,
                'total_pages': total_pages,
                'has_more': False,
                'next_page': None,
                'prev_page': None
            },
            'meta': meta,
            'fetch_summary': {
                'pages_fetched': 1,
                'total_pages': total_pages,
                'items_fetched': len(all_data),
                'total_items': total_items
            }
        }
    
    # Fetch remaining pages
    failed_pages = []
    successful_pages = 1  # Already have page 1
    
    for page_num in range(2, total_pages + 1):
        try:
            logger.info(f"Fetching page {page_num}/{total_pages}")
            
            # Add delay to avoid rate limiting
            if delay_between_pages > 0:
                logger.debug(f"Waiting {delay_between_pages} seconds before next request")
                time.sleep(delay_between_pages)
            
            page_data = get_catalog_page(
                page_num=page_num,
                bearer_token=bearer_token,
                segment=segment,
                lang=lang,
                max_retries=max_retries,
                timeout=timeout
            )
            
            if page_data.get('success', False):
                page_items = page_data.get('data', [])
                all_data.extend(page_items)
                successful_pages += 1
                logger.info(f"Successfully fetched page {page_num} with {len(page_items)} items")
            else:
                logger.warning(f"Page {page_num} returned success=false")
                failed_pages.append(page_num)
                
        except RazomAPIError as e:
            logger.error(f"Failed to fetch page {page_num}: {e.message}")
            failed_pages.append(page_num)
            
            # If too many pages are failing, stop the process
            if len(failed_pages) > total_pages * 0.2:  # More than 20% failure rate
                logger.error(f"Too many page failures ({len(failed_pages)}/{page_num-1}), stopping fetch")
                raise RazomAPIError(
                    f"Failed to fetch catalog: too many page failures ({len(failed_pages)} pages failed)",
                    response_data={'failed_pages': failed_pages}
                )
        
        except Exception as e:
            logger.error(f"Unexpected error fetching page {page_num}: {e}")
            failed_pages.append(page_num)
    
    # Log summary
    items_fetched = len(all_data)
    logger.info(f"Catalog fetch completed: {successful_pages}/{total_pages} pages, {items_fetched} items")
    
    if failed_pages:
        logger.warning(f"Failed to fetch {len(failed_pages)} pages: {failed_pages}")
    
    # Return complete catalog
    result = {
        'success': True,
        'data': all_data,
        'pagination': {
            'current_page': total_pages,  # Set to last page
            'per_page': pagination.get('per_page', 200),
            'total': total_items,
            'total_pages': total_pages,
            'has_more': False,
            'next_page': None,
            'prev_page': total_pages - 1 if total_pages > 1 else None
        },
        'meta': meta,
        'fetch_summary': {
            'pages_fetched': successful_pages,
            'total_pages': total_pages,
            'failed_pages': failed_pages,
            'items_fetched': items_fetched,
            'total_items': total_items,
            'success_rate': successful_pages / total_pages if total_pages > 0 else 0
        }
    }
    
    return result


if __name__ == "__main__":
    try:
        access_token = get_access_token()
        print(f"Access token: {access_token}")

        segment = 'eur'  # gur or eur
        catalog_data = get_catalog_full(bearer_token=access_token, segment=segment)
        
        if segment == 'eur':
            filename = 'data/stocklists/full_eur_catalog.json'
        elif segment == 'gur':
            filename = 'data/stocklists/full_gur_catalog.json'
        else:
            raise ValueError(f"Unsupported segment: {segment}")

        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w') as catalog_file:
            json.dump(catalog_data, catalog_file)

        output_path = f'data/stocklists/{segment}.csv'
        df = pipeline_gur_eur_data(input_json_data=catalog_data, output_path=output_path)
        
    except RazomAPIError as e:
        logger.error(f"API Error: {e.message}")
        if e.status_code:
            logger.error(f"Status Code: {e.status_code}")
        if e.response_data:
            logger.error(f"Response Data: {e.response_data}")
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")