import re
from typing import List, Optional
from pathlib import Path

def validate_file_type(filename: str) -> bool:
    """
    Validate if the uploaded file type is supported
    
    Args:
        filename: Name of the uploaded file
        
    Returns:
        bool: True if file type is supported
    """
    if not filename:
        return False
    
    allowed_extensions = {'.pdf', '.docx'}
    file_extension = Path(filename).suffix.lower()
    
    return file_extension in allowed_extensions

def validate_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email format is valid
    """
    if not email:
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def validate_file_size(file_size: int, max_size_mb: int = 10) -> bool:
    """
    Validate file size is within limits
    
    Args:
        file_size: File size in bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        bool: True if file size is valid
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return 0 < file_size <= max_size_bytes

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    if not filename:
        return "unnamed_file"
    
    # Remove or replace dangerous characters
    safe_chars = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Ensure filename is not too long
    if len(safe_chars) > 255:
        name_part = safe_chars[:240]
        extension = Path(filename).suffix
        safe_chars = name_part + extension
    
    return safe_chars

def validate_risk_score(score: int) -> bool:
    """
    Validate risk score is within acceptable range
    
    Args:
        score: Risk score to validate
        
    Returns:
        bool: True if score is valid (1-10)
    """
    return isinstance(score, int) and 1 <= score <= 10

def validate_analysis_data(analysis_data: dict) -> List[str]:
    """
    Validate contract analysis data structure
    
    Args:
        analysis_data: Dictionary containing analysis results
        
    Returns:
        List[str]: List of validation errors (empty if valid)
    """
    errors = []
    
    # Required fields
    required_fields = ['risk_score', 'summary', 'risky_clauses', 'missing_protections', 'detailed_analysis']
    
    for field in required_fields:
        if field not in analysis_data:
            errors.append(f"Missing required field: {field}")
    
    # Validate risk score
    if 'risk_score' in analysis_data:
        if not validate_risk_score(analysis_data['risk_score']):
            errors.append("Risk score must be an integer between 1 and 10")
    
    # Validate summary
    if 'summary' in analysis_data:
        if not isinstance(analysis_data['summary'], str) or len(analysis_data['summary'].strip()) == 0:
            errors.append("Summary must be a non-empty string")
    
    # Validate risky clauses structure
    if 'risky_clauses' in analysis_data:
        if not isinstance(analysis_data['risky_clauses'], list):
            errors.append("Risky clauses must be a list")
        else:
            for i, clause in enumerate(analysis_data['risky_clauses']):
                if not isinstance(clause, dict):
                    errors.append(f"Risky clause {i} must be a dictionary")
                    continue
                
                required_clause_fields = ['clause_type', 'description', 'recommendation']
                for field in required_clause_fields:
                    if field not in clause:
                        errors.append(f"Risky clause {i} missing field: {field}")
    
    # Validate missing protections structure
    if 'missing_protections' in analysis_data:
        if not isinstance(analysis_data['missing_protections'], list):
            errors.append("Missing protections must be a list")
        else:
            for i, protection in enumerate(analysis_data['missing_protections']):
                if not isinstance(protection, dict):
                    errors.append(f"Missing protection {i} must be a dictionary")
                    continue
                
                required_protection_fields = ['protection_type', 'description', 'importance']
                for field in required_protection_fields:
                    if field not in protection:
                        errors.append(f"Missing protection {i} missing field: {field}")
    
    return errors

def clean_text_content(text: str) -> str:
    """
    Clean and normalize text content for analysis
    
    Args:
        text: Raw text content
        
    Returns:
        str: Cleaned text content
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', text)
    
    # Remove control characters except newlines and tabs
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)
    
    # Normalize line endings
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
    
    return cleaned.strip()

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        str: Formatted file size (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"

def extract_key_terms(text: str, max_terms: int = 20) -> List[str]:
    """
    Extract key terms from contract text for indexing/search
    
    Args:
        text: Contract text
        max_terms: Maximum number of terms to extract
        
    Returns:
        List[str]: List of key terms
    """
    if not text:
        return []
    
    # Common contract terms to look for
    contract_keywords = [
        'agreement', 'contract', 'party', 'parties', 'terms', 'conditions',
        'liability', 'damages', 'termination', 'breach', 'confidential',
        'intellectual property', 'payment', 'delivery', 'warranty',
        'indemnification', 'dispute', 'arbitration', 'governing law'
    ]
    
    # Find keywords that appear in the text
    found_terms = []
    text_lower = text.lower()
    
    for keyword in contract_keywords:
        if keyword in text_lower:
            found_terms.append(keyword)
    
    # Extract additional important words (simplified approach)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
    word_freq = {}
    
    for word in words:
        word_lower = word.lower()
        if word_lower not in ['this', 'that', 'with', 'have', 'will', 'shall', 'from', 'they', 'been', 'were']:
            word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
    
    # Get most frequent words
    frequent_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:max_terms - len(found_terms)]
    found_terms.extend([word for word, _ in frequent_words])
    
    return found_terms[:max_terms]
