# WhatsApp Chat Backend Simulation

## Run Instructions
1. Install requirements: `pip install fastapi uvicorn sqlalchemy pydantic`
2. Run server: `uvicorn main:app --reload`
3. Access API Documentation at `http://127.0.0.1:8000/docs` to test the endpoints.

## Authentication
The `POST /webhook/whatsapp` endpoint is protected. 
Include header: `Authorization: Bearer my_secret_token_123`