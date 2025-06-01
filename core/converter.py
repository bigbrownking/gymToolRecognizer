import base64
import io
from io import BytesIO
from PIL import Image


def image_to_base64(image: Image.Image) -> str:
    try:
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{image_base64}"

    except Exception as e:
        print(f"Error converting image to base64: {str(e)}")
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
        except Exception as fallback_error:
            print(f"Fallback PNG conversion also failed: {str(fallback_error)}")
            raise


CLASS_NAMES = {
    0: "Chin Dip",
    1: "Аэробные степперы",
    2: "Беговая дорожка",
    3: "Велотренажер",
    4: "Гакк Присед",
    5: "Гимнастический мяч",
    6: "Груша для битья",
    7: "Жим лежа",
    8: "Жим ногами",
    9: "Жим от груди сидя на тренажере",
    10: "Жим от плеч",
    11: "Икроножный тренажер",
    12: "Кабельный кроссовер",
    13: "Канат",
    14: "Ленточный эспандер",
    15: "Машина Смита",
    16: "Отведение и сведение бедра",
    17: "Отжимания в положении сидя",
    18: "Поролоновый валик",
    19: "Разгибание ног",
    20: "Разгибание рук",
    21: "Разгибание спины",
    22: "Роликовые тренажеры для пресса",
    23: "Сгибание рук",
    24: "Тренажер GHD",
    25: "Тренажер для бокового подъема",
    26: "Тренажер для пресса",
    27: "Тренажер для сгибания ног",
    28: "Тренажер для тренировки грудных мышц и дельтовидной мышцы",
    29: "Тяга верхнего блока",
    30: "Тяга нижнего блока",
    31: "Упоры для отжиманий",
    32: "Эллиптический тренажер"
}