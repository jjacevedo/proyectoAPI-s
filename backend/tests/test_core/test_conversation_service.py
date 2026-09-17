from app.models.message import Message
from app.services.conversation_service import build_contextual_prompt


def test_build_contextual_prompt_returns_prompt_unchanged_without_history():
    assert build_contextual_prompt([], "hola") == "hola"


def test_build_contextual_prompt_includes_prior_turns_in_order():
    history = [
        Message(role="user", content="¿Qué es Python?"),
        Message(role="assistant", content="Un lenguaje de programación."),
    ]

    result = build_contextual_prompt(history, "¿Y JavaScript?")

    assert "Usuario: ¿Qué es Python?" in result
    assert "Asistente: Un lenguaje de programación." in result
    assert result.index("Usuario: ¿Qué es Python?") < result.index("Asistente: Un lenguaje de programación.")
    assert "Nuevo mensaje del usuario: ¿Y JavaScript?" in result
