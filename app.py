import streamlit as st
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import zipfile
import os

# --- НАСТРОЙКИ ПО УМОЛЧАНИЮ ---
HEADER_FONT_NAME = './fonts/Montserrat-Bold.ttf' 
TEXT_FONT_NAME = './fonts/Montserrat-Regular.ttf' 
HEADER_FONT_SIZE = 70 
TEXT_FONT_SIZE = 40
WATERMARK_FONT_SIZE = 26 
TEXT_COLOR = (255, 255, 255)
WATERMARK_ALPHA = 130 

GLASS_BLUR_RADIUS = 40     
GLASS_DARKEN_ALPHA = 170   
BORDER_ALPHA = 30          

# --- ФУНКЦИЯ СТЕКЛА ---
def create_editorial_glass(base_img, panel_width, panel_height, glass_x, glass_y):
    glass_size = (panel_width, panel_height)
    target_region = base_img.crop((glass_x, glass_y, glass_x + panel_width, glass_y + panel_height))
    blurred_bg = target_region.filter(ImageFilter.GaussianBlur(GLASS_BLUR_RADIUS))
    darken = Image.new('RGBA', glass_size, (0, 0, 0, GLASS_DARKEN_ALPHA))
    blurred_bg.alpha_composite(darken)
    draw_border = ImageDraw.Draw(blurred_bg)
    draw_border.rectangle((0, 0, panel_width-1, panel_height-1), outline=(255, 255, 255, BORDER_ALPHA), width=1)
    return blurred_bg

def parse_raw_text(content):
    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
    slides = []
    for block in blocks:
        lines = block.split('\n')
        title = lines[0].strip()
        text = " ".join([line.strip() for line in lines[1:]])
        slides.append({"title": title, "text": text})
    return slides

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="Генератор Каруселей", page_icon="⬛", layout="centered")

st.title("The генератор")
st.markdown("Создавай карусели для соц-сетей прямо с телефона. By @dze")

# 1. Загрузка фона
uploaded_bg = st.file_uploader("1. Загрузи фон (JPG/PNG) - он автоматически кропнется в формат 3:4", type=['png', 'jpg', 'jpeg'])

# 2. Настройки брендинга
st.subheader("2. Брендинг и Текст")
user_watermark = st.text_input("Твой никнейм (водяной знак)", value="")

# 3. Ввод текста
default_text = """ЗАГОЛОВОК 1
Текст 1

ЗАГОЛОВОК 2
Текст 2"""

text_input = st.text_area("Текст карусели (Пустая строка разделяет слайды)", value=default_text, height=250)

# 4. Кнопка генерации
if st.button("Сгенерировать карусель", type="primary"):
    if not uploaded_bg:
        st.error("Сначала загрузи фон!")
    elif not text_input.strip():
        st.error("Вставь текст!")
    else:
        with st.spinner("Рендерим матовое стекло..."):
            slides_data = parse_raw_text(text_input)
            
            # РАБОТАЕМ С ФОНОМ
            # --- УМНЫЙ КРОП ПОД 4:5 (1080x1350) ---
            input_img = Image.open(uploaded_bg).convert("RGB")
            w, h = input_img.size
            target_ratio = 1080 / 1350
            input_ratio = w / h

            if input_ratio > target_ratio:
                # Картинка слишком широкая (пейзаж) — режем бока
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                base_img = input_img.crop((left, 0, left + new_w, h))
            else:
                # Картинка слишком узкая (9:16) — режем верх/низ
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                base_img = input_img.crop((0, top, w, top + new_h))

            # Ресайзим до финального размера 1080x1350
            base_img = base_img.resize((1080, 1350), Image.Resampling.LANCZOS).convert("RGBA")

            # ШРИФТЫ
            try:
                h_font = ImageFont.truetype(HEADER_FONT_NAME, HEADER_FONT_SIZE)
                t_font = ImageFont.truetype(TEXT_FONT_NAME, TEXT_FONT_SIZE)
                w_font = ImageFont.truetype(TEXT_FONT_NAME, WATERMARK_FONT_SIZE)
            except IOError:
                st.error("Ошибка: шрифты не найдены в папке ./fonts/")
                st.stop()

            generated_images = []

            for i, slide in enumerate(slides_data):
                img = base_img.copy()
                
                h_lines = textwrap.wrap(slide['title'], width=14)
                t_lines = textwrap.wrap(slide['text'], width=28) 
                
                padding_top = 110 
                padding_bottom = 90
                title_line_height = 85
                text_line_height = 60
                space_between = 120 
                
                total_text_height = (len(h_lines) * title_line_height) + space_between + (len(t_lines) * text_line_height)
                panel_height = padding_top + total_text_height + padding_bottom
                panel_width = 900
                
                glass_x = (final_w - panel_width) // 2
                glass_y = (final_h - panel_height) // 2 - 20 
                
                # Создаем стекло строго под регионом
                glass_panel = create_editorial_glass(base_img, panel_width, panel_height, glass_x, glass_y)
                img.alpha_composite(glass_panel, (glass_x, glass_y))
                
                draw = ImageDraw.Draw(img) 
                
                # РИСУЕМ ПОЛЬЗОВАТЕЛЬСКИЙ ВОТЕРМАРК
                if user_watermark:
                    bbox = draw.textbbox((0, 0), user_watermark, font=w_font)
                    w_width = bbox[2] - bbox[0]
                    w_x = (final_w - w_width) // 2
                    w_y = 60 
                    draw.text((w_x, w_y), user_watermark, font=w_font, fill=(255, 255, 255, WATERMARK_ALPHA))
                
                # ТЕКСТ
                current_y = glass_y + padding_top
                margin_x = glass_x + 80 

                for line in h_lines:
                    draw.text((margin_x, current_y), line, font=h_font, fill=TEXT_COLOR)
                    current_y += title_line_height

                current_y += space_between 
                
                for line in t_lines:
                    draw.text((margin_x, current_y), line, font=t_font, fill=TEXT_COLOR)
                    current_y += text_line_height

                # ТОЧКИ
                total_slides = len(slides_data)
                dots_y = 1250
                dot_radius = 12
                dots_x_start = (final_w - (total_slides * 40 - 20)) // 2
                for j in range(total_slides):
                    x = dots_x_start + j * 40
                    color = TEXT_COLOR if j == i else (150, 150, 150, 200)
                    draw.ellipse((x, dots_y, x + dot_radius * 2, dots_y + dot_radius * 2), fill=color)
                
                generated_images.append(img.convert("RGB"))

            # ВЫВОД
            st.success("Карусель готова!")
            
            cols = st.columns(2)
            for idx, g_img in enumerate(generated_images):
                cols[idx % 2].image(g_img, use_container_width=True)

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, g_img in enumerate(generated_images):
                    img_byte_arr = io.BytesIO()
                    g_img.save(img_byte_arr, format='JPEG', quality=95)
                    zip_file.writestr(f"slide_{idx+1}.jpg", img_byte_arr.getvalue())

            st.download_button(
                label="📥 Скачать всю карусель (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="carousel.zip",
                mime="application/zip",
                type="primary"
            )
