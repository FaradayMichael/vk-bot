from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image


class ImageCaptioning:

    def __init__(
            self,
            model_name: str = "Salesforce/blip-image-captioning-base",
            cache_dir: str = "./cache",
    ):
        self._processor = BlipProcessor.from_pretrained(model_name, cache_dir=cache_dir)
        self._model = BlipForConditionalGeneration.from_pretrained(model_name, cache_dir=cache_dir)

    def get_image_description(self, image_path: str) -> str:
        image = Image.open(image_path).convert("RGB")
        inputs = self._processor(image, return_tensors="pt")
        out = self._model.generate(**inputs, max_length=100)
        result = self._processor.decode(out[0], skip_special_tokens=True)
        return result
