import re


def duration_to_month(value: str):
    pattern = re.findall(r"(\d+)\s*(\w+)", value.strip().lower())
    if not pattern:
        raise ValueError("Invalid format")

    total_months = 0
    month_units = {"mon", "mons", "month", "months"}
    year_units = {"year", "years"}

    for num_str, unit in pattern:
        num = int(num_str)
        if unit in month_units:
            total_months += num
        elif unit in year_units:
            total_months += num * 12
        else:
            raise NotImplementedError(f"Unit '{unit}' not supported")

    return total_months
