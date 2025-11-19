import speech_recognition as sr


def speech_to_text(filepath: str) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(filepath) as source:
        audio = recognizer.record(source)

    text = ""
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
    except sr.UnknownValueError:
        print("Не удалось распознать речь")
    except sr.RequestError as e:
        print(f"Ошибка сервиса; {e}")

    return text
