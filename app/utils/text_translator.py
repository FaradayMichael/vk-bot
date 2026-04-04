from transformers import MarianTokenizer, MarianMTModel


class TextTranslator:

    def __init__(
            self,
            model_name: str = "",
            cache_dir: str = "./cache",
    ):
        self._tokenizer = MarianTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
        self._model = MarianMTModel.from_pretrained(model_name, cache_dir=cache_dir)

    def translate(self, text: str) -> str:
        inputs = self._tokenizer(text, return_tensors="pt")
        output = self._model.generate(**inputs, max_new_tokens=100)
        out_text = self._tokenizer.batch_decode(output, skip_special_tokens=True)
        return out_text[0] or ""


class EnRuTextTranslator(TextTranslator):
    def __init__(
            self,
            model_name: str = "Helsinki-NLP/opus-mt-en-ru",
            *args,
            **kwargs,
    ):
        super().__init__(model_name, *args, **kwargs)
