from datetime import datetime

def get_formatted_date(date):
    """Format date for display"""
    if not date:
        return "N/A"
    return date.strftime("%d-%m-%Y %H:%M")

def is_past_days(date, days):
    """Check if date is more than specified days in the past"""
    if not date:
        return False
    
    days_difference = (datetime.utcnow() - date).days
    return days_difference >= days