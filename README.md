# Glow & Grace Salon AI Booking Agent

A multilingual AI-powered salon appointment assistant built as a portfolio project.

The assistant supports:

- English, Urdu, Roman Urdu, and mixed-language conversations
- Voice input and AI voice replies
- Appointment booking
- Cancellation
- Rescheduling
- Real-time Google Calendar availability
- Google Sheets booking records
- SQLite session management
- RAG-based salon FAQs
- FastAPI backend
- Docker deployment
- WhatsApp Cloud API integration tested in Meta's development environment

## Tech Stack

- Python
- FastAPI
- OpenAI API
- LangChain
- ChromaDB
- SQLite
- Google Calendar API
- Google Sheets API
- Docker
- Caddy
- WhatsApp Cloud API

## Architecture

```text
Customer
   |
   v
WhatsApp / Browser UI
   |
   v
FastAPI
   |
   +-- Language Detection
   +-- Speech-to-Text / Text-to-Speech
   +-- Intent Router
   +-- RAG Knowledge Base
   +-- Booking / Cancellation / Rescheduling
   +-- SQLite Session Store
   +-- Google Calendar
   +-- Google Sheets
