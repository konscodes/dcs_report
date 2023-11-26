from datetime import datetime, timedelta

def calculate_overtime(start_time, end_time):
    time_format = '%Y-%m-%d %H:%M:%S'
    
    window_start = start_time.replace(hour=9, minute=0, second=0)
    window_end = start_time.replace(hour=18, minute=0, second=0)
    
    # If the start time is after the window end or end time is before the window start
    if start_time >= window_end or end_time <= window_start:
        return (end_time - start_time).total_seconds() / 3600  # Total hours outside the window
    
    # Calculating the duration outside the window
    if start_time < window_start:
        outside_before_start = (window_start - start_time).total_seconds() / 3600
    else:
        outside_before_start = 0
    
    if end_time > window_end:
        outside_after_end = (end_time - window_end).total_seconds() / 3600
    else:
        outside_after_end = 0
    
    overtime = outside_before_start + outside_after_end
    return overtime

# Example usage:
start_time = datetime.strptime('2023-11-25 09:35:00', '%Y-%m-%d %H:%M:%S')
end_time = datetime.strptime('2023-11-25 19:00:00', '%Y-%m-%d %H:%M:%S')

overtime = calculate_overtime(start_time, end_time)
print(f"Total overtime: {overtime:.2f} hours")
