from app.core.config import settings

print('OPENAI_API_KEY:', settings.llm.openai_api_key.get_secret_value())
