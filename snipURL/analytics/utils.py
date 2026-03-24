"""
Utility functions for analytics.
"""
from user_agents import parse


def get_client_ip(request):
    """
    Extract client IP address from request.
    Handles proxies and load balancers.

    Args:
        request: Django HTTP request

    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent_string):
    """
    Parse user agent string to extract browser, OS, and device type.

    Args:
        user_agent_string (str): User agent string

    Returns:
        dict: Parsed user agent data with keys: browser, os, device_type
    """
    if not user_agent_string:
        return {
            'browser': None,
            'os': None,
            'device_type': 'unknown'
        }

    user_agent = parse(user_agent_string)

    # Determine device type
    if user_agent.is_bot:
        device_type = 'bot'
    elif user_agent.is_mobile:
        device_type = 'mobile'
    elif user_agent.is_tablet:
        device_type = 'tablet'
    elif user_agent.is_pc:
        device_type = 'desktop'
    else:
        device_type = 'unknown'

    return {
        'browser': f"{user_agent.browser.family} {user_agent.browser.version_string}",
        'os': f"{user_agent.os.family} {user_agent.os.version_string}",
        'device_type': device_type
    }


def get_country_from_ip(ip_address):
    """
    Get country and city from IP address using geolocation.

    Note: This is a placeholder. In production, integrate with a service like:
    - MaxMind GeoIP2
    - ipapi.co
    - ip-api.com

    Args:
        ip_address (str): IP address

    Returns:
        dict: {country: str, city: str} or None values if lookup fails
    """
    # Placeholder - integrate with actual geolocation service
    # For now, return None to avoid external dependencies
    return {
        'country': None,
        'city': None
    }


def create_click_event(url, request):
    """
    Create a ClickEvent from a request.

    Args:
        url: Url model instance
        request: Django HTTP request

    Returns:
        ClickEvent: Created click event
    """
    from .models import ClickEvent

    ip_address = get_client_ip(request)
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    referer = request.META.get('HTTP_REFERER', '')

    # Parse user agent
    ua_data = parse_user_agent(user_agent_string)

    # Get geolocation (optional)
    geo_data = get_country_from_ip(ip_address)

    click_event = ClickEvent.objects.create(
        url=url,
        ip_address=ip_address,
        user_agent=user_agent_string,
        referer=referer,
        country=geo_data.get('country'),
        city=geo_data.get('city'),
        browser=ua_data.get('browser'),
        os=ua_data.get('os'),
        device_type=ua_data.get('device_type', 'unknown')
    )

    return click_event
