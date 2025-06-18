from datetime import date, datetime, time, timedelta, timezone

JST = timezone(timedelta(hours=9))

# UTC
now = datetime.now(JST).timestamp()
print(now)

# day = "2025-04-29"
# time = "15:30"

d = date(2025, 4, 30)
t = time(hour=21, minute=50)

# UTC
dt = datetime.combine(d, t).timestamp()
print(dt)

# UTC -> JST
jst_datetime = datetime.fromtimestamp(dt, tz=JST)
print(jst_datetime)
