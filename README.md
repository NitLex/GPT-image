# GPT Image — конвейер креативов

Python-пайплайн, который:

1. Берёт папку с референсами
2. Отправляет их в **GPT Image API** (`/v1/images/edits`)
3. Подставляет нужный **оффер** и **заголовок**
4. Генерирует сразу несколько вариантов
5. Автоматически масштабирует под баннерные размеры (`300×250`, `728×90`, `970×250` и др.)

Так можно быстро получать пачку креативов в едином фирменном стиле.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

cp .env.example .env
# вставьте OPENAI_API_KEY в .env

# положите референсы в references/
cp config.example.yaml config.yaml
# отредактируйте offer / headline / brand

python generate_creatives.py --config config.yaml
```

## Пример из CLI

```bash
python generate_creatives.py \
  --references references \
  --offer "Скидка 30% на первый заказ" \
  --headline "Доставка за 15 минут" \
  --cta "Заказать сейчас" \
  --brand "BrandName" \
  --variants 4 \
  --sizes 300x250 728x90 970x250 160x600 300x600 320x50 \
  --mode batch \
  --quality high
```

Проверка без расхода токенов:

```bash
python generate_creatives.py \
  --offer "Скидка 30%" \
  --headline "Новый оффер" \
  --dry-run -v
```

Только ресайз уже готовых мастеров:

```bash
python resize_only.py output/<run>/masters --sizes 300x250 728x90 970x250
```

## Как это работает

```text
references/*.png
        │
        ▼
  GPT Image API  ← offer + headline + CTA
  (несколько вариантов)
        │
        ▼
   output/.../masters/*.png
        │
        ▼
   локальный resize (Pillow)
        │
        ▼
   output/.../sizes/**/300x250, 728x90, 970x250, ...
```

- **mode=batch** — все референсы уходят в один запрос (единый стиль)
- **mode=per_reference** — отдельная генерация по каждому файлу
- **resize_mode=cover** — заполняет размер с center-crop
- **resize_mode=contain** — вписывает целиком и дополняет `fill_color`

Мастер генерируется в API-размере (`1536x1024` / `1024x1024` / `auto` и т.д.), а точные баннерные форматы получаются локально — это быстрее и дешевле, чем дергать API на каждый size.

## Структура вывода

```text
output/
  20260726_121500_dostavka-za-15-minut/
    manifest.txt
    prompt_batch_v01.txt
    masters/
      batch_v01.png
      batch_v02.png
    sizes/
      batch_v01/
        batch_v01_medium_rectangle_300x250.png
        batch_v01_leaderboard_728x90.png
        ...
```

## Конфиг

См. `config.example.yaml`. Ключевые поля:

| Поле | Назначение |
|------|------------|
| `offer` / `headline` / `cta` | Тексты на креативе |
| `variants` | Сколько вариантов сгенерировать |
| `model` | `gpt-image-1.5` (по умолчанию) или `gpt-image-2` |
| `master_size` | Размер генерации в API |
| `sizes` | Список баннерных размеров |
| `mode` | `batch` или `per_reference` |

## Тесты

```bash
pip install -r requirements.txt pytest
pytest -q
```

## Замечания

- Нужен доступ к GPT Image models в вашем OpenAI-проекте.
- Референсы лучше класть чистые, без чужих логотипов/товарных знаков, если бренд другой.
- Для очень «длинных» баннеров (`728×90`, `970×90`) иногда полезнее `contain` или отдельные landscape-мастера.
