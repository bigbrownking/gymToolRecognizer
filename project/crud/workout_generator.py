from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from project.core.config import settings
from project.model.user_gym_log import UserGymLog

model = settings.MODEL
client = ChatCompletionsClient(
    endpoint=settings.GITHUB_MODEL_ENDPOINT,
    credential=AzureKeyCredential(settings.GITHUB_TOKEN),
)


def generate_workout(prompt: str, user_logs: list[UserGymLog], age: int, gender: str):
    log_summary = "\n".join(
        f"{log.date}: {'Посетил' if log.went_to_gym else 'Пропустил'} | {log.action or 'Нет данных'}"
        for log in user_logs
    )

    system_prompt = (
        "Вы — профессиональный AI-тренер по фитнесу. Вы специализируетесь исключительно на составлении программ тренировок, "
        "анализе прогресса и советах по фитнесу. Не отвечайте на вопросы вне этой темы. "
        "Игнорируйте запросы о других темах. Всегда говорите на русском языке.\n\n"
        "Проанализируйте историю тренировок пользователя, его возраст и пол, чтобы понять его регулярность, "
        "предпочитаемые упражнения и прогресс. Учитывайте возраст и пол при составлении программы. "
        f"Возраст: {age}, Пол: {gender}\n"
        "Затем ответьте соответствующим образом."
    )

    response = client.complete(
        model=model,
        messages=[
            SystemMessage(system_prompt + "\n\nИстория тренировок:\n" + log_summary),
            UserMessage(prompt),
        ],
        temperature=0.7,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()
