"""
Template API client for fetching templates from Lambda.
"""

import os
import logging
import requests
from typing import List, Optional, Dict
from .models import TemplateSpec

logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get(
    'TEMPLATE_API_URL',
    'https://qcol9gunw4.execute-api.eu-central-1.amazonaws.com'
)


class TemplateClient:
    """Client for interacting with the template API."""

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = 10):
        """
        Initialize template client.

        Args:
            base_url: Base URL for the template API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def list_templates(self) -> List[Dict]:
        """
        Fetch template summaries.

        Returns:
            List of template summary dictionaries
        """
        try:
            url = f"{self.base_url}/templates"
            logger.info(f"Fetching templates from {url}")
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            templates = data.get('templates', [])
            logger.info(f"Successfully fetched {len(templates)} templates")
            return templates
        except requests.RequestException as e:
            logger.exception(f"Error fetching templates from {self.base_url}: {e}")
            return []

    def get_template(self, template_id: str) -> Optional[TemplateSpec]:
        """
        Fetch full template specification.

        Args:
            template_id: Unique template identifier

        Returns:
            TemplateSpec object or None if error
        """
        try:
            url = f"{self.base_url}/templates/{template_id}"
            logger.info(f"Fetching template {template_id} from {url}")
            response = requests.get(url, timeout=self.timeout)

            logger.debug(f"API response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"API response data keys: {list(data.keys())}")

            if data.get('success'):
                template = TemplateSpec.from_dict(data['template'])
                logger.info(f"Successfully loaded template {template_id}")
                return template
            else:
                logger.error(f"API returned success=false for template {template_id}: {data}")
                return None

        except requests.RequestException as e:
            logger.exception(f"Request error fetching template {template_id}: {e}")
            return None
        except KeyError as e:
            logger.exception(f"Missing key in template response for {template_id}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error parsing template {template_id}: {e}")
            return None
