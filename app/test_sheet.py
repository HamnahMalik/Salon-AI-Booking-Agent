from sheet_service import save_booking_to_sheet

test_booking = {
    "name": "Test Customer",
    "phone": "03001234567",
    "service": "Manicure",
    "staff": "Hina",
    "date": "2026-10-15",
    "time": "2:00 PM",
    "calendar_event_id": "test_event_123",
}

result = save_booking_to_sheet(
    test_booking
)

print(result)

