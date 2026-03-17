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
WATERMARK_ALPHA = 130 

GLASS_BLUR_RADIUS = 40     
GLASS_DARKEN_ALPHA = 170   
BORDER_ALPHA = 30          

# --- ФУНКЦИИ ---
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

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
uploaded_bg = st.file_uploader("1. Загрузи фон (JPG/PNG) - он автоматически кропнется в формат 4:5", type=['png', 'jpg', 'jpeg'])

# 2. Настройки брендинга
st.subheader("2. Брендинг")
user_watermark = st.text_input("Твой никнейм (водяной знак)", value="")

# 3. Настройки дизайна
st.subheader("3. Дизайн")
col1, col2, col3 = st.columns(3)
with col1:
    use_glass = st.toggle("Матовое стекло", value=True)
with col2:
    text_position = st.selectbox("Позиция текста", ["Посередине", "Снизу", "Сверху"])
with col3:
    text_color_hex = st.color_picker("Цвет текста", "#FFFFFF")

space_between = st.slider("Отступ между заголовком и текстом", min_value=30, max_value=250, value=120, step=10)

# 4. Ввод текста
st.subheader("4. Контент")
default_text = """ЗАГОЛОВОК 1
Текст 1

ЗАГОЛОВОК 2
Текст 2"""
text_input = st.text_area("Текст карусели (Пустая строка разделяет слайды)", value=default_text, height=250)

# 5. Кнопка генерации
if st.button("Сгенерировать карусель", type="primary"):
    if not uploaded_bg:
        st.error("Сначала загрузи фон!")
    elif not text_input.strip():
        st.error("Вставь текст!")
    else:
        with st.spinner("Рендерим кадры..."):
            slides_data = parse_raw_text(text_input)
            
            # РАБОТАЕМ С ФОНОМ (УМНЫЙ КРОП)
            input_img = Image.open(uploaded_bg).convert("RGB")
            w, h = input_img.size
            final_w, final_h = 1080, 1350 
            target_ratio = final_w / final_h
            input_ratio = w / h

            if input_ratio > target_ratio:
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                base_img = input_img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                base_img = input_img.crop((0, top, w, top + new_h))

            base_img = base_img.resize((final_w, final_h), Image.Resampling.LANCZOS).convert("RGBA")

            # ШРИФТЫ И ЦВЕТ
            user_rgb_color = hex_to_rgb(text_color_hex)
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
                
                total_text_height = (len(h_lines) * title_line_height) + space_between + (len(t_lines) * text_line_height)
                panel_height = padding_top + total_text_height + padding_bottom
                panel_width = 900
                
                # ЛОГИКА ПОЗИЦИОНИРОВАНИЯ
                glass_x = (final_w - panel_width) // 2
                
                if text_position == "Сверху":
                    glass_y = 150 
                elif text_position == "Снизу":
                    glass_y = final_h - panel_height - 80 # Уменьшенный отступ без точек
                else: 
                    glass_y = (final_h - panel_height) // 2 - 20 
                
                # ЛОГИКА СТЕКЛА
                if use_glass:
                    glass_panel = create_editorial_glass(base_img, panel_width, panel_height, glass_x, glass_y)
                    img.alpha_composite(glass_panel, (glass_x, glass_y))
                
                draw = ImageDraw.Draw(img) 
                
                # ВОТЕРМАРК
                if user_watermark:
                    bbox = draw.textbbox((0, 0), user_watermark, font=w_font)
                    w_width = bbox[2] - bbox[0]
                    w_x = (final_w - w_width) // 2
                    w_y = 60 
                    draw.text((w_x, w_y), user_watermark, font=w_font, fill=(*user_rgb_color, WATERMARK_ALPHA))
                
                # ТЕКСТ
                current_y = glass_y + padding_top
                margin_x = glass_x + 80 

                for line in h_lines:
                    draw.text((margin_x, current_y), line, font=h_font, fill=user_rgb_color)
                    current_y += title_line_height

                current_y += space_between 
                
                for line in t_lines:
                    draw.text((margin_x, current_y), line, font=t_font, fill=user_rgb_color)
                    current_y += text_line_height
                
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
