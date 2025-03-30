import base64

from plotly.graph_objs import Figure

from utils.dataurl import DataURL


def figure_to_image_dataurl(figure: Figure) -> DataURL:
    img_bytes = figure.to_image(format='png')
    base64_data = base64.b64encode(img_bytes)
    return DataURL.make(mimetype="image/png", data=base64_data, charset=None, base64=True)
