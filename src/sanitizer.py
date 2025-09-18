"""
Input Sanitization Module
Provides comprehensive input validation and sanitization for all external data
"""

import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class Sanitizer:
    """Comprehensive input sanitization for security"""
    
    # Dangerous patterns that could indicate injection attempts
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers
        r'<iframe',  # Iframes
        r'<object',  # Objects
        r'<embed',  # Embeds
        r'\.\./|\.\.\\\\'  # Path traversal
        r';\s*(DROP|DELETE|INSERT|UPDATE|EXEC|EXECUTE)',  # SQL injection
        r'--\s*$',  # SQL comments
        r'union\s+select',  # SQL union
        r'\\x[0-9a-fA-F]{2}',  # Hex encoding
        r'%[0-9a-fA-F]{2}',  # URL encoding attacks
    ]
    
    @classmethod
    def sanitize_string(cls, value: Optional[str], max_length: int = 10000) -> str:
        """
        Sanitize a string input
        
        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if value is None:
            return ''
        
        if not isinstance(value, str):
            value = str(value)
        
        # Truncate to max length
        if len(value) > max_length:
            logger.warning(f"String truncated from {len(value)} to {max_length} chars")
            value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # HTML escape
        value = html.escape(value)
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected and removed: {pattern[:20]}")
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Remove control characters except newlines and tabs
        value = ''.join(char for char in value if char in '\n\t' or (ord(char) >= 32 and ord(char) != 127))
        
        return value.strip()
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize a filename for safe storage
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        if not filename:
            return 'unnamed'
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        name, ext = '', ''
        if '.' in filename:
            parts = filename.rsplit('.', 1)
            name = parts[0][:100]
            ext = '.' + parts[1][:10]
        else:
            name = filename[:100]
        
        result = name + ext
        return result if result else 'unnamed'
    
    @classmethod
    def sanitize_url(cls, url: str) -> Optional[str]:
        """
        Validate and sanitize URLs
        
        Args:
            url: URL to validate
            
        Returns:
            Sanitized URL or None if invalid
        """
        if not url:
            return None
        
        try:
            parsed = urlparse(url)
            
            # Only allow http/https
            if parsed.scheme not in ['http', 'https']:
                logger.warning(f"Invalid URL scheme: {parsed.scheme}")
                return None
            
            # Check for localhost/private IPs
            if parsed.hostname:
                if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                    logger.warning("Localhost URL blocked")
                    return None
                
                # Check for private IP ranges
                if re.match(r'^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)', parsed.hostname):
                    logger.warning("Private IP URL blocked")
                    return None
            
            return url
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return None
    
    @classmethod
    def sanitize_rfp_data(cls, rfp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize an entire RFP data structure
        
        Args:
            rfp: Raw RFP data
            
        Returns:
            Sanitized RFP data
        """
        if not rfp:
            return {}
        
        sanitized = {}
        
        # String fields to sanitize
        string_fields = [
            'title', 'description', 'fullParentPathName', 'type',
            'naicsCode', 'classificationCode', 'noticeId', 
            'solicitationNumber', 'department', 'office'
        ]
        
        for field in string_fields:
            if field in rfp:
                max_len = 10000 if field == 'description' else 500
                sanitized[field] = cls.sanitize_string(rfp.get(field), max_length=max_len)
        
        # URL fields
        url_fields = ['uiLink', 'additionalInfoLink']
        for field in url_fields:
            if field in rfp and rfp[field]:
                sanitized[field] = cls.sanitize_url(rfp[field])
        
        # Date fields - pass through as-is (validated elsewhere)
        date_fields = ['postedDate', 'responseDeadLine', 'archiveDate']
        for field in date_fields:
            if field in rfp:
                sanitized[field] = rfp[field]
        
        # Numeric fields
        numeric_fields = ['pointOfContact']
        for field in numeric_fields:
            if field in rfp:
                val = rfp[field]
                if isinstance(val, (int, float)):
                    sanitized[field] = val
                elif isinstance(val, str) and val.isdigit():
                    sanitized[field] = int(val)
        
        # Arrays
        if 'attachments' in rfp and isinstance(rfp['attachments'], list):
            sanitized['attachments'] = [
                cls.sanitize_attachment(att) for att in rfp['attachments'][:10]  # Limit attachments
            ]
        
        return sanitized
    
    @classmethod
    def sanitize_attachment(cls, attachment: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize attachment data"""
        if not attachment:
            return {}
        
        return {
            'name': cls.sanitize_filename(attachment.get('name', 'unnamed')),
            'url': cls.sanitize_url(attachment.get('url', '')),
            'type': cls.sanitize_string(attachment.get('type', ''), max_length=50)
        }
    
    @classmethod
    def validate_score(cls, score: Any) -> int:
        """
        Validate and normalize scores to 1-10 range
        
        Args:
            score: Input score value
            
        Returns:
            Valid score between 1 and 10
        """
        try:
            score_int = int(score)
            if score_int < 1:
                return 1
            elif score_int > 10:
                return 10
            return score_int
        except (TypeError, ValueError):
            logger.warning(f"Invalid score value: {score}, defaulting to 1")
            return 1
    
    @classmethod
    def sanitize_for_sheets(cls, value: Any) -> str:
        """
        Sanitize value for Google Sheets insertion
        
        Args:
            value: Value to sanitize
            
        Returns:
            String safe for sheets
        """
        if value is None:
            return ''
        
        # Convert to string
        str_val = str(value)
        
        # Remove formulas (starts with = or +)
        if str_val.startswith(('=', '+', '-', '@')):
            str_val = "'" + str_val
        
        # Limit length for sheets
        if len(str_val) > 50000:  # Google Sheets cell limit
            str_val = str_val[:49997] + '...'
        
        # Remove null bytes and control characters
        str_val = ''.join(char for char in str_val if ord(char) >= 32 or char in '\n\t')
        
        return str_val