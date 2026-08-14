from financial_research.config.settings import Settings, get_settings


def get_llm(settings: Settings | None = None):
    """Return the configured chat model without exposing provider details elsewhere."""
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_model)
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
        )
    if provider in {"google", "gemini"}:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            google_api_key=settings.google_api_key,
            model=settings.google_model,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
