# FigCraft v0.7.0: свой форк в Coolify

Эта конфигурация собирает **исходники текущего checkout**, а не скачивает готовый
FigCraft из релизов автора. Ветка `selfhost` создана от upstream `v0.7.0`
(`47438dd4a2e8b49a7e6bb3dfd480262dadc37f12`). `main` не изменяется.

Два сервиса: `figcraft-web` (статический браузерный редактор, Nginx на **8080**)
и `figcraft-server` (документы и WebSocket, **47900**). HTTPS и маршруты настраивает
прокси Coolify. Порты контейнеров на хост не публикуются.

## 1. Подключить репозиторий

В Coolify создай Application из Git-репозитория — не Docker Compose Empty:

| Поле | Значение |
| --- | --- |
| Repository | `https://github.com/Astler/figcraft` |
| Branch | `selfhost` |
| Build Pack / Build strategy | Docker Compose / Compose |
| Base Directory | `/` |
| Docker Compose Location | `/docker-compose.yml` |

Сохрани и загрузи Compose. **Raw / deploy file as-is не включай**: маршруты,
сеть и метки прокси должен добавлять Coolify. Config-файлы встроены в образы,
поэтому bind mounts из checkout и Preserve repository для этой схемы не нужны.

## 2. Настроить два домена и переменную

Замени примеры своими доменами. DNS обоих адресов должен указывать на сервер
Coolify; для обычного HTTPS должны быть доступны TCP 80/443.

В Environment Variables:

```dotenv
FIGCRAFT_PUBLIC_URL=wss://collab.example.com/
CARGO_BUILD_JOBS=2
RUST_LOG=info
```

Обязательна только `FIGCRAFT_PUBLIC_URL`. Это **публичный адрес backend**, не адрес
редактора. Нужен завершающий `/`; нельзя добавлять `?key=`, credentials, путь или
внутренний Docker-порт. Не записывай настоящий серверный ключ в Git или эту переменную.

Переменная должна быть доступна и при сборке, и во время работы. Compose передаёт её
в `build.args.FIGCRAFT_DEFAULT_SERVER` редактора и в окружение backend. Если интерфейс
Coolify показывает переключатели Buildtime / Runtime, включи оба.

В Domains настрой:

| Service | Protocol | Domain (пример) | Внутренний порт |
| --- | --- | --- | ---: |
| `figcraft-web` | https | `figcraft.example.com` | **8080** |
| `figcraft-server` | https | `collab.example.com` | **47900** |

Если интерфейс предлагает одно поле URL:

```text
figcraft-web:    https://figcraft.example.com:8080
figcraft-server: https://collab.example.com:47900
```

Порт в настройке маршрута выбирает **внутренний** порт контейнера. Пользователь
открывает обычный `https://figcraft.example.com/`; backend использует обычный
`wss://collab.example.com/` на публичном 443. Ports Mappings не заполняй.

Публичный URL валидируется перед сборкой редактора и при запуске backend. Адрес
с ключом отклоняется без печати его значения. Домен пока не известен — используй
выданный Coolify HTTPS-домен backend, с заменой `https://` на `wss://`.

## 3. Deploy и проверка

Нажми Deploy. В Deployment Logs проверь успешное завершение обеих сборок,
затем состояние сервисов и Runtime Logs. Открой редактор и проверь:

```sh
curl --fail --silent --show-error https://figcraft.example.com/healthz
curl --fail --silent --show-error https://collab.example.com/healthz
```

Оба endpoint должны отвечать `ok`. Healthcheck редактора проверяет Nginx, а не
работоспособность всего WASM-приложения: редактор также нужно открыть в браузере.
При проблемах с графикой предусмотрен upstream-режим `https://figcraft.example.com/?webgl`.

Для `No available server` / 502 сначала проверь runtime-логи, healthcheck и порт
домена. Web слушает **8080**, не 80. Для проблем с компиляцией смотри именно build-логи.

## 4. Серверный ключ и первый документ

В Terminal контейнера **figcraft-server** выбери `/bin/sh` и выполни:

```sh
figcraft-server-run key
```

Это обёртка штатной команды, использующая конфиг и текущий публичный URL:

```sh
figcraft-server --config /etc/figcraft-server/server.toml \
  --public-url "$FIGCRAFT_PUBLIC_URL" key
```

Полученный `wss://.../?key=...` — административный адрес. В desktop FigCraft
v0.7.0 открой документ → **File → Publish to server…** (либо Share → Advanced →
Publish to another server…) и вставь его. В браузерном редакторе используй
**File → Join live session…** с полученной **ссылкой документа**. Участникам
отправляй edit/view-ссылки документа, не серверный ключ. Эта упаковка не меняет
возможности публикации исходного приложения v0.7.0.

Адрес твоего backend уже встроен как default в браузерную сборку. Сохранённое ранее
значение в Preferences имеет приоритет: при необходимости выбери свой адрес в
**Preferences → Server for online sharing**. При смене backend URL сделай **Redeploy
со сборкой**, а не просто Restart: клиентское значение задаётся во время компиляции.

## Данные, доступ и резервные копии

`figcraft-data` подключён к `/data`. В нём находятся документы, журналы и ключ.
Coolify может добавить префикс к имени тома: фактическое имя смотри в Persistent
Storage. Том переживает перезапуск и обычный redeploy того же ресурса. Создание
другого приложения Coolify не переносит данные автоматически.

Не удаляй том и не запускай `docker compose down -v` на рабочей установке. Не
запускай два backend одновременно на одном томе. Backend работает как UID/GID
10001:10001; существующий импортированный том должен иметь подходящие права.

**Автоматических бэкапов здесь нет.** Для консистентной копии останови backend,
сохрани весь том и затем запусти его. Храни копии отдельно от сервера и защищай
их как секреты: они содержат ключ и документы. Проверь восстановление на отдельной
тестовой установке до любых обновлений или удаления старого ресурса.

`open_publish = false`: новые файлы публикуют только обладатели серверного ключа.
Аккаунтов и личных ACL в этой версии нет; доступ к документу определяется его
ссылкой. Сам сайт редактора публичный. Это не система входа пользователей и не
сквозное шифрование. Не включай публичную публикацию без отдельной настройки
лимитов, доверенного прокси и правил хранения.

Лимит снимка документа — 32 МиБ, с запасом до клиентского лимита сообщения.
Автоматическое удаление по сроку неактивности отключено. Остальные серверные
параметры находятся в `deploy/coolify/server.toml`; после изменения нужен redeploy.

## Сборка и проверки

Rust закреплён на 1.95.0, Trunk — 0.21.14; исходные зависимости приложения
используют `Cargo.lock` (`--locked`). Шрифтовый build input берётся из
`storytold/craft-fonts` по тому же commit, что upstream-релиз. Отдельные шрифтовые
файлы в этот репозиторий не добавляются; notices включены в образ редактора.
Runtime-теги `debian:bookworm-slim` и `nginx:stable-alpine` получают обновления при
обновлении базовых образов, поэтому вся цепочка образов не закреплена по digest.

Нужен Docker с BuildKit и доступом к Docker Hub, crates.io, GitHub и серверам Rust.
Сборка рассчитана на обычный Linux AMD64/ARM64 без кросс-компиляции. Начальная
компиляция тяжелее запуска готовых контейнеров. `CARGO_BUILD_JOBS=1` уменьшает
параллелизм; это не гарантирует сборку на сервере с любым объёмом памяти. BuildKit
сохраняет кэш Cargo для повторных сборок.

Быстрые тесты (Python 3.11+, без сторонних Python-пакетов):

```sh
python3 -m unittest discover -s deploy/coolify -v
```

Тесты проверяют форму URL, отказ на credentials, приватный TOML, shell-синтаксис,
передачу аргументов и `umask`. Проверка Compose пропускается, когда Docker отсутствует.
Они **не заменяют** компиляцию и проверку приложения в браузере.

На машине с Docker, из корня репозитория:

```sh
cp deploy/coolify/.env.example .env
# Измени FIGCRAFT_PUBLIC_URL в .env до сборки.
docker compose config --quiet
docker compose build
```

Образы сами выполняют `figcraft-server ... check` и `nginx -t` при сборке.
Полный Rust/Docker build и подключение браузера нужно подтвердить по результатам
деплоя. Ветка `selfhost` не подтягивает upstream автоматически: обновляй осознанно,
после резервного копирования, и сохраняй эти файлы при merge.

## Исходная документация

- [Сервер и модель доступа](../../docs/server.md)
- [Настройка default server](../../docs/releasing.md#the-default-server)
- [Coolify: Docker Compose](https://coolify.io/docs/applications/builds/docker-compose)
- [Coolify: домены](https://coolify.io/docs/core/networking/domains)
