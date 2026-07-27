1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   echo "OPENAI_API_KEY=sk-..." > .env
   uvicorn app.main:app --reload 
   ```

2. Testing
```bash
curl -X POST "[http://127.0.0.1:8000/next-question](http://127.0.0.1:8000/next-question)" \ -H "Content-Type: application/json" \ -d '{ "conversation": [ {"speaker": "agent", "text": "Can I verify benefits for John Smith?"}, {"speaker": "insurance", "text": "Sure."}, {"speaker": "agent", "text": "Is the deductible met?"}, {"speaker": "insurance", "text": "No."}, {"speaker": "agent", "text": "How much remains?"}, {"speaker": "insurance", "text": "$850."} ] }'
```