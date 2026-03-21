from calendar import monthrange
from datetime import date, timedelta


def month_bounds(month_value):
    month_start = month_value.replace(day=1)
    month_end = month_start.replace(day=monthrange(month_start.year, month_start.month)[1])
    return month_start, month_end


def daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def is_working_day(current_date, holiday_dates=None):
    holiday_dates = holiday_dates or set()
    return current_date.weekday() != 6 and current_date not in holiday_dates


def get_working_dates(start_date, end_date, holiday_dates=None):
    holiday_dates = holiday_dates or set()
    return [current for current in daterange(start_date, end_date) if is_working_day(current, holiday_dates)]


def financial_year_bounds(reference_date):
    if reference_date.month >= 4:
        start = date(reference_date.year, 4, 1)
        end = date(reference_date.year + 1, 3, 31)
    else:
        start = date(reference_date.year - 1, 4, 1)
        end = date(reference_date.year, 3, 31)
    return start, end
