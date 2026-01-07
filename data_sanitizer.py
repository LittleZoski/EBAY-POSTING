"""
Data Sanitizer: Clean Amazon scraped data for eBay compliance
Removes policy violations before listing creation
"""

import re
from typing import Dict, Any, List


class DataSanitizer:
    """Sanitizes Amazon product data to comply with eBay policies"""

    # Patterns to remove from descriptions
    VIOLATION_PATTERNS = [
        # External URLs
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        r'www\.[^\s<>"{}|\\^`\[\]]+',

        # Amazon-specific text that suggests external linking
        r'Visit\s+https?://[^\s]+\s+for\s+full\s+details',
        r'See\s+more\s+product\s+details',
        r'›\s*See\s+more\s+product\s+details',
        r'\[See\s+more\]',
        r'View\s+on\s+Amazon',

        # Contact information patterns
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone numbers
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses

        # Social media handles
        r'@\w+',
        r'facebook\.com/\w+',
        r'instagram\.com/\w+',
        r'twitter\.com/\w+',

        # JavaScript code fragments
        r'var\s+\w+\s*=',
        r'P\.when\([^\)]+\)',
        r'ue\.count\([^\)]+\)',
        r'A\.declarative\([^\)]+\)',
        r'function\s*\([^\)]*\)\s*\{',
        r'\}\s*\)\s*;',

        # HTML/Script tags that shouldn't be in descriptions
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
    ]

    # Phrases that suggest external transactions
    EXTERNAL_TRANSACTION_PHRASES = [
        'contact us directly',
        'email us at',
        'call us at',
        'visit our website',
        'visit our store',
        'buy direct from',
        'purchase outside',
        'off-platform',
        'dm for details',
        'message for price',
    ]

    def sanitize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize entire product object for eBay compliance.
        Returns a new dict with cleaned data.
        """
        sanitized = product.copy()

        # Clean description
        if 'description' in sanitized:
            sanitized['description'] = self.sanitize_text(sanitized['description'])

        # Clean bullet points
        if 'bulletPoints' in sanitized:
            sanitized['bulletPoints'] = [
                self.sanitize_text(bp) for bp in sanitized['bulletPoints']
            ]

        # Clean title (less aggressive, but still check)
        if 'title' in sanitized:
            sanitized['title'] = self.sanitize_text(sanitized['title'], aggressive=False)

        # Clean specifications
        if 'specifications' in sanitized:
            sanitized['specifications'] = self.sanitize_specifications(
                sanitized['specifications']
            )

        return sanitized

    def sanitize_text(self, text: str, aggressive: bool = True) -> str:
        """
        Clean text content to remove policy violations.

        Args:
            text: The text to sanitize
            aggressive: If True, apply all sanitization rules. If False, only remove
                       critical violations (for titles, etc.)
        """
        if not text:
            return text

        cleaned = text

        # Always remove URLs (critical violation)
        for pattern in [
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            r'www\.[^\s<>"{}|\\^`\[\]]+',
        ]:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        if aggressive:
            # Remove all violation patterns
            for pattern in self.VIOLATION_PATTERNS:
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

            # Remove external transaction phrases
            for phrase in self.EXTERNAL_TRANSACTION_PHRASES:
                cleaned = re.sub(
                    r'\b' + re.escape(phrase) + r'\b',
                    '',
                    cleaned,
                    flags=re.IGNORECASE
                )

        # Clean up whitespace
        cleaned = self._clean_whitespace(cleaned)

        return cleaned.strip()

    def sanitize_specifications(self, specs: Dict[str, str]) -> Dict[str, str]:
        """
        Clean product specifications.
        Removes JavaScript code and other violations.
        """
        sanitized_specs = {}

        for key, value in specs.items():
            if not value:
                continue

            value_str = str(value)

            # Skip specs that are primarily JavaScript code
            if any(indicator in value_str for indicator in [
                'var ', 'function(', 'P.when', 'ue.count', '.execute(',
                'A.declarative', 'window.', 'document.'
            ]):
                # This spec is mostly/all JavaScript, skip it entirely
                continue

            # Clean the value
            cleaned_value = self.sanitize_text(value_str, aggressive=True)

            # Only include if there's meaningful content left
            # (JavaScript code will be completely removed, leaving empty string)
            if cleaned_value and len(cleaned_value.strip()) > 1:
                sanitized_specs[key] = cleaned_value

        return sanitized_specs

    def _clean_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace while preserving structure"""
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)

        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove spaces at start/end of lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text

    def validate_clean(self, text: str) -> tuple[bool, List[str]]:
        """
        Validate that text is clean and compliant.
        Returns (is_clean, list_of_violations_found)
        """
        violations = []

        # Check for URLs
        if re.search(r'https?://|www\.', text, re.IGNORECASE):
            violations.append('Contains URLs')

        # Check for email addresses
        if re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', text):
            violations.append('Contains email addresses')

        # Check for phone numbers
        if re.search(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', text):
            violations.append('Contains phone numbers')

        # Check for JavaScript code
        if re.search(r'var\s+\w+|function\s*\(|P\.when|ue\.count', text):
            violations.append('Contains JavaScript code')

        # Check for external transaction phrases
        for phrase in self.EXTERNAL_TRANSACTION_PHRASES:
            if re.search(r'\b' + re.escape(phrase) + r'\b', text, re.IGNORECASE):
                violations.append(f'Contains phrase: "{phrase}"')

        return (len(violations) == 0, violations)


# Global sanitizer instance
data_sanitizer = DataSanitizer()
