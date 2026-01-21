"""
Template API client for fetching templates from Lambda.
"""

import os
import requests
from typing import List, Optional, Dict
from .models import TemplateSpec

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
            response = requests.get(
                f"{self.base_url}/templates",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get('templates', [])
        except requests.RequestException as e:
            print(f"Error fetching templates: {e}")
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
            response = requests.get(
                f"{self.base_url}/templates/{template_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                return TemplateSpec.from_dict(data['template'])
            return None

        except requests.RequestException as e:
            print(f"Error fetching template {template_id}: {e}")
            return None
