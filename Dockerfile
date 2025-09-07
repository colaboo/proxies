FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /src
COPY pyproject.toml uv.lock ./

# Установка зависимостей в виртуальное окружение
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --link-mode=copy

FROM python:3.13-slim

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends tor curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN useradd --create-home --shell /bin/bash app
# RUN apt-get update && apt-get install -y \
#     wget \
#     curl \
#     unzip \
#     ca-certificates \
#     fonts-liberation \
#     libappindicator3-1 \
#     libnss3 \
#     libxss1 \
#     libxtst6 \
#     xdg-utils \
#     libgdk-pixbuf2.0-0 \
#     libx11-xcb1 \
#     libu2f-udev \
#     libpci3 \
#     libnspr4 \
#     libxcomposite1 \
#     libasound2 \
#     libxrandr2 \
#     libgbm1 \
#     libatk-bridge2.0-0 \
#     libatk1.0-0 \
#     libgdk-pixbuf2.0-0 \
#     libepoxy0 \
#     lsb-release \
#     && apt-get clean

# # Install Chromium (or other browser)
# RUN apt-get update && apt-get install -y chromium-driver

# Set environment variables for headless mode and Chromium path
# ENV DISPLAY=:99
# ENV CHROME_BIN=/usr/bin/chromium


# RUN apt-get update
# & apt-get install git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
COPY --from=builder --chown=app:app /src/.venv /src/.venv

WORKDIR /src

# Копирование исходного кода
COPY --chown=app:app . .
RUN mkdir -p /src/keys && chown -R app:app /src/keys
USER app

# Настройка PATH для использования venv
ENV PATH="/src/.venv/bin:$PATH"
ENV PYTHONPATH=/src

#RUN killall tor
# TODO: tor запускается во время билда, а нужно во время рантайма
# RUN tor --RunAsDaemon 1 --CookieAuthentication 0 --ControlPort 8118 --SocksPort 9050
EXPOSE 8000

CMD uv run python src/main.py
