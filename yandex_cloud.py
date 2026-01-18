import openai

from src.config import get_yandex_cloud_settings


YANDEX_CLOUD_BASE_URL = "https://rest-assistant.api.cloud.yandex.net/v1"


def main() -> None:
    settings = get_yandex_cloud_settings()

    client = openai.OpenAI(
        api_key=settings.yandex_api_key,
        base_url=YANDEX_CLOUD_BASE_URL,
        project=settings.yandex_folder_id,
    )

    response = client.responses.create(
        model=f"gpt://{settings.yandex_folder_id}/qwen3-235b-a22b-fp8/latest",
        input="Придумай 3 необычные идеи для стартапа в сфере путешествий.",
        temperature=0.8,
        max_output_tokens=1500,
    )

    print(response.output[0].content[0].text)


if __name__ == "__main__":
    main()
