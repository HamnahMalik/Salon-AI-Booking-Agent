from openai import OpenAI

client = OpenAI()


def detect_intent(message: str) -> str:
    prompt = f"""
Classify the customer's message into exactly one intent:

- salon_question
- book_appointment
- cancel_appointment
- reschedule_appointment
- greeting
- unknown

Important rules:

- If the message contains a greeting AND a salon-related question,
  classify it as salon_question.

Examples:

"hello what services do you offer?"
salon_question

"hi, how much is a facial?"
salon_question

"hello"
greeting

"what services do you offer?"
salon_question

"I want to book a facial"
book_appointment

"cancel my appointment"
cancel_appointment

"move my appointment to Friday"
reschedule_appointment

Return ONLY the intent name.

Customer message:
{message}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text.strip()
