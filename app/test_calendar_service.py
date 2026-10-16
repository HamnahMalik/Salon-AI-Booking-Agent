from calendar_service import (
    get_available_slots,
    get_busy_periods,
)


DATE = "2026-10-12"


print("\nBUSY PERIODS")
print(
    get_busy_periods(
        DATE
    )
)


print(
    "\nAVAILABLE MANICURE "
    "AFTERNOON SLOTS"
)

slots = get_available_slots(
    service_name="Manicure",
    date_string=DATE,
    time_preference="afternoon"
)

for slot in slots:
    print(slot)
