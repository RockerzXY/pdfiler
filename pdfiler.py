#!/usr/bin/env python3

import os
import sys
import time
import click
from PIL import Image, UnidentifiedImageError


def is_image_file(file_path):
    """
    Проверяет, можно ли открыть файл как изображение.
    Возвращает False для GIF.
    """
    try:
        with Image.open(file_path) as img:
            img.verify()  # Проверка целостности файла изображения
        # Отключаем GIF (и файлы без определения формата)
        with Image.open(file_path) as img:
            return img.format not in ('GIF', None)
    except (UnidentifiedImageError, IOError):
        return False


def process_image(file_path, quality):
    """
    Открывает изображение, при необходимости сохраняет во временный файл с указанным качеством.
    Возвращает объект Image.
    """
    try:
        img = Image.open(file_path)
        if img.mode in ('RGBA', 'P'):  # Если есть альфа-канал или палитра, преобразуем
            img = img.convert('RGB')

        if quality:
            from io import BytesIO
            temp_buffer = BytesIO()
            img.save(temp_buffer, format='JPEG', quality=quality)
            temp_buffer.seek(0)
            img = Image.open(temp_buffer)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        return img
    except Exception as e:
        click.echo(f"Ошибка обработки изображения {file_path}: {e}", err=True)
        sys.exit(1)  # Завершаем выполнение при ошибке обработки изображения


def get_images_from_directory(directory):
    """
    Возвращает список файлов-изображений из указанной директории,
    отсортированных по времени изменения.
    """
    files = [f for f in os.listdir(directory) if is_image_file(os.path.join(directory, f))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)))
    return [os.path.join(directory, f) for f in files]


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('images', nargs=-1, type=click.Path())
@click.option('-d', '--input-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help='Директория с изображениями. При использовании -d файлы должны быть указаны как относительные имена или auto-stamp.')
@click.option('-q', '--quality', type=click.IntRange(1, 100), default=80,
              help='Качество изображений внутри итогового PDF (1-100).')
@click.option('-o', '--output', required=True,
              help='Путь для сохранения итогового PDF файла.')
@click.option('--dry-run', is_flag=True, help='Показать файлы, которые будут обработаны, без создания PDF.')
@click.option('-r', '--remove-source', is_flag=True, help='Удалить исходные файлы после создания PDF.')
@click.option('-v', '--verbose', is_flag=True, help='Подробный вывод процесса.')
def main(images, input_dir, quality, output, dry_run, remove_source, verbose):
    """
    Консольная утилита для создания PDF из набора изображений.

    Примеры использования:

      pdfiler 1.jpg 2.jpg -o gallery.pdf -q 80 -v  
      (явно указываются файлы)

      pdfiler auto-stamp -d /path/to/images -o gallery.pdf -q 80 -v  
      (берутся все файлы из указанной директории, отсортированные по timestamp)

    При использовании -d файлы должны быть указаны как относительные имена (без путей) или auto-stamp.
    """
    start_time = time.time()

    # Если указан input_dir, то файлы должны быть заданы как относительные имена
    if input_dir:
        if not images:
            click.echo("Ошибка: при использовании -d необходимо указать файлы (относительные имена или auto-stamp).", err=True)
            sys.exit(1)
        # Если какой-либо файл задан как абсолютный путь – ошибка.
        for img in images:
            if os.path.isabs(img):
                click.echo("Ошибка: при использовании -d файлы должны быть указаны без полного пути.", err=True)
                sys.exit(1)
        # Если первый аргумент auto-stamp, берем все файлы из директории
        if images[0] == "auto-stamp":
            images = get_images_from_directory(input_dir)
            if verbose:
                click.echo(f"Найдено изображений в директории '{input_dir}': {len(images)}")
        else:
            # Формируем абсолютные пути, добавляя input_dir как базовую директорию
            images = [os.path.join(input_dir, img) for img in images]
    else:
        if images and images[0] == "auto-stamp":
            images = get_images_from_directory(os.getcwd())
            if verbose:
                click.echo(f"Найдено изображений в текущей директории: {len(images)}")
        else:
            images = [os.path.abspath(img) for img in images if os.path.isfile(img)]

    if not images:
        click.echo("Нет валидных изображений для обработки.", err=True)
        sys.exit(1)

    valid_images = []
    for img_path in images:
        if not os.path.isfile(img_path): 
            if verbose:
                click.echo(f"Файл не найден: {img_path}", err=True)
            continue
        if not is_image_file(img_path):
            if verbose:
                click.echo(f"Файл не является изображением: {img_path}", err=True)
            continue
        valid_images.append(img_path)

    if verbose:
        click.echo(f"Файлов после проверки: {len(valid_images)}")

    if not valid_images:
        click.echo("Нет валидных изображений для обработки.", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("Файлы, которые будут обработаны:")
        for idx, file_path in enumerate(valid_images, start=1):
            click.echo(f"{idx} --- {file_path}")
        sys.exit(0)

    processed_images = []
    for idx, file_path in enumerate(valid_images, start=1):
        img = process_image(file_path, quality)
        if img:
            processed_images.append(img)
            if verbose:
                click.echo(f"Страница {idx} --- {file_path}")

    if not processed_images:
        click.echo("Не удалось обработать ни одно изображение.", err=True)
        sys.exit(1)

    # Проверка директории для output файла
    output_dir = os.path.dirname(os.path.abspath(output))
    if output_dir and not os.path.exists(output_dir):
        click.echo(f"Директория для сохранения не существует: {output_dir}", err=True)
        sys.exit(1)

    try:
        processed_images[0].save(output, "PDF", resolution=100.0, save_all=True, append_images=processed_images[1:])
        elapsed_time = time.time() - start_time
        file_size = os.path.getsize(output) / (1024 * 1024)
        click.echo(f"Файл {output} ({file_size:.2f} MB) создан за {elapsed_time:.2f} секунд.")
        if remove_source:
            for img in valid_images:
                os.remove(img)
            click.echo("Исходные файлы удалены.")
    except Exception as e:
        click.echo(f"Ошибка при сохранении PDF: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
