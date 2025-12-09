import re


def clean_reply_to_text(body_text):
    """
    Удаляет все строки, начинающиеся с '>', и предыдущую строку-заголовок
    цитаты из текста.

    Args:
        body_text (str): Исходный текст тела электронного письма.

    Returns:
        str: Очищенный текст, содержащий только новый контент.
    """
    if body_text is None:
        return None

    lines = body_text.split('\n')
    
    # 1. Находим индекс первой строки, которая начинается с '>'
    first_reply_line_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('>'):
            first_reply_line_index = i
            break
            
    if first_reply_line_index == -1:
        # Если цитата не найдена, возвращаем исходный текст
        return body_text

    # 2. Определяем, является ли строка перед цитатой заголовком цитаты.
    header_index = first_reply_line_index - 1
    
    if header_index >= 0:
        potential_header_line = lines[header_index].strip()
        
        # Простая эвристика для заголовка: содержит '@', заканчивается ':'
        if ('@' in potential_header_line or potential_header_line.endswith(':')):
            # Устанавливаем точку отсечения, чтобы исключить и заголовок
            cutoff_index = header_index
        else:
            # Если строка перед '>' не похожа на заголовок, то это часть нового сообщения.
            cutoff_index = first_reply_line_index
    else:
        # Если '>' - это первая строка, просто удаляем ее и все, что идет дальше.
        cutoff_index = first_reply_line_index

    # 3. Возвращаем только строки до точки отсечения
    cleaned_body = '\n'.join(lines[:cutoff_index]).strip()
    
    return cleaned_body