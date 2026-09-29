# Telegram 24/7 Live Stream Bot

بوت Telegram خاص بالمالك لإدارة فيديوهات محفوظة على الخادم وتشغيلها كبث مباشر متواصل داخل قناة Telegram. كل إدارة البوت تتم من خلال Inline Keyboard؛ الأمر الوحيد المستخدم للدخول هو `/start`.

## Architecture

```text
Owner
  │
  ▼
Telegram Bot API ── aiogram 3 ── Arabic owner panel
  │
  ├── Uploads → videos/ → ffprobe metadata
  ├── Metadata/state → MongoDB
  └── StreamController → FFmpeg → Telegram RTMP ingest → Channel Live Stream

Pyrogram user client
  └── validates channel access and reads channel metadata when configured
```

### لماذا نحتاج كل جزء؟

- **aiogram**: يستقبل الرسائل ويشغّل Inline Keyboard وCallbackQuery.
- **Pyrogram**: يوفّر Telegram client إضافياً للتحقق من القناة والوظائف التي لا يغطيها Bot API.
- **FFmpeg**: يحوّل كل فيديو إلى H.264/AAC بدقة ومعدل إطارات ثابتين ويرسله عبر RTMP.
- **MongoDB**: يحفظ الفيديوهات، Playlists، إعدادات RTMP، وحالة البث بعد إعادة تشغيل الخادم.
- **Docker أو systemd**: يعيدان تشغيل الخدمة تلقائياً بعد تعطل العملية أو إعادة تشغيل الخادم.

## طريقة العمل

1. المالك يرسل `/start`.
2. يتم التحقق من `OWNER_ID` الرقمي في كل رسالة وكل Callback. لا يتم استخدام username.
3. من زر **رفع فيديو** يرسل المالك الفيديو. ينزل إلى القرص داخل `videos/` باسم UUID، ثم يُفحص عبر `ffprobe` وتُحفظ بياناته في MongoDB.
4. يمكن تشغيل فيديو واحد في Loop أو تشغيل Playlist بالتتابع والعودة لأول فيديو.
5. عند نهاية الفيديو بشكل طبيعي ينتقل النظام للفيديو التالي أو يعيد نفس الفيديو.
6. عند خروج FFmpeg بخطأ، يسجل الخطأ ويعيد المحاولة. بعد `FFMPEG_RESTART_LIMIT` يرسل تنبيهاً ثم يواصل المحاولة بتأخير محدود.
7. عند إيقاف الخدمة، تُحفظ الحالة في MongoDB. عند تشغيلها من جديد، يعاد تشغيل البث إذا كانت الحالة السابقة فعالة.

## Folder Structure

```text
telegram-live-bot/
├── bot.py
├── config.py
├── database.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── telegram-live-bot.service
├── README.md
├── handlers/
│   ├── common.py
│   ├── start.py
│   ├── menu.py
│   ├── upload.py
│   ├── videos.py
│   ├── playlists.py
│   ├── stream.py
│   ├── settings.py
│   └── stats.py
├── services/
│   ├── controller.py
│   ├── ffmpeg.py
│   ├── telegram_stream.py
│   ├── storage.py
│   └── monitor.py
├── models/
├── keyboards/
├── utils/
├── videos/
├── logs/
└── sessions/
```

## Dependencies

- Python 3.12+
- FFmpeg and ffprobe
- MongoDB 6+ (Docker Compose uses MongoDB 8)
- `aiogram 3.x`
- `Pyrogram 2.x` and `TgCrypto`
- `motor`
- `python-dotenv`
- `psutil`

## إعداد Telegram

### 1. إنشاء البوت

1. افتح `@BotFather`.
2. أنشئ Bot جديداً وخذ `BOT_TOKEN`.
3. أرسل `/userinfobot` أو استخدم أي طريقة موثوقة لمعرفة Telegram numeric ID الخاص بك وضعه في `OWNER_ID`.
4. أضف البوت Admin في القناة مع صلاحية إدارة البث إذا كانت مطلوبة من إعدادات القناة.

### 2. إنشاء Live Stream

1. أنشئ Live Stream من القناة.
2. انسخ **RTMP URL** و **Stream Key** من Telegram.
3. ضع القيمتين في `.env` أو أدخلهما من صفحة **الإعدادات** داخل البوت.
4. لا تضع Stream Key في Git أو داخل الكود. البوت يخفيه افتراضياً في لوحة الإعدادات ولا يسجله في اللوج.

> Telegram لا يوفّر مساراً عاماً وآمناً يمكن الاعتماد عليه لاستخراج Stream Key لكل أنواع القنوات تلقائياً عبر Bot API أو Pyrogram. لذلك يطلب النظام المفتاح من المالك مرة واحدة ويحفظه في MongoDB. Pyrogram مستخدم للتحقق من القناة والوصول إلى بياناتها، وليس لتخمين المفتاح.

### 3. الحصول على API_ID و API_HASH

1. سجّل الدخول إلى `my.telegram.org`.
2. افتح **API development tools**.
3. أنشئ تطبيقاً وانسخ `API_ID` و `API_HASH` إلى `.env`.
4. أول تشغيل لـ Pyrogram قد يحتاج جلسة مستخدم Telegram. احفظ ملف الجلسة داخل `sessions/` ولا ترفعه إلى Git.

## إعداد البيئة

```bash
cd telegram-live-bot
cp .env.example .env
```

ضع القيم التالية على الأقل:

```dotenv
BOT_TOKEN=...
OWNER_ID=123456789
API_ID=123456
API_HASH=...
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=telegram_live_bot
CHANNEL_ID=@your_channel
RTMP_URL=rtmp://...
STREAM_KEY=...
```

ابدأ بقيم البث الافتراضية التالية وعدّلها إذا احتجت:

```dotenv
VIDEO_BITRATE=2500k
AUDIO_BITRATE=128k
RESOLUTION=1280x720
FPS=30
FFMPEG_PRESET=veryfast
```

## التشغيل المحلي على Linux

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg mongodb
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

لا تستخدم أسماء ملفات من المستخدم مباشرة كمسارات. النظام ينظف الاسم ويحفظ الملف داخل `videos/` باسم UUID.

## Docker Compose

يشغّل Compose البوت وMongoDB، ويحفظ الفيديوهات واللوج والجلسات في Volumes/مجلدات محلية:

```bash
cp .env.example .env
# عدّل .env
docker compose up -d --build
docker compose logs -f bot
```

يجب أن يبقى `MONGO_URI=mongodb://mongo:27017` عند استخدام Compose.

## systemd

انسخ المشروع إلى `/opt/telegram-live-bot`، ثم:

```bash
sudo cp telegram-live-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-live-bot
sudo systemctl start telegram-live-bot
sudo systemctl status telegram-live-bot
```

تأكد من وضع `.env` داخل `/opt/telegram-live-bot/.env` ومن تثبيت FFmpeg وMongoDB. لا تشغّل Docker وsystemd معاً لنفس النسخة حتى لا يعمل مثيلان من البوت.

## الفيديوهات الكبيرة

التنزيل يتم إلى Disk عبر aiogram ولا يتم تجميع الفيديو في RAM. حدود تنزيل ملفات Telegram تتغير حسب Bot API وطريقة الاستضافة. إذا كانت الملفات تتجاوز حدود Bot API المتاحة على خادمك، استخدم Local Bot API Server أو ارفع الفيديو عبر قناة/مسار يدعم الحجم المطلوب ثم أعد تصميم مسار الاستيراد حسب بيئتك. يجب دائماً التأكد من مساحة القرص قبل رفع ملفات كبيرة.

## إدارة المساحة

- `LOW_STORAGE_GB=10` يرسل تنبيهاً عند نزول المساحة الحرة تحت الحد.
- صفحة **الإحصائيات** تعرض المساحة، RAM، CPU، العملية، وقت البدء، وعدد الاستعادات.
- خيار **حذف الفيديوهات القديمة** يحذف كل الفيديوهات المسجلة في قاعدة البيانات والملفات التابعة لها. استخدمه فقط بعد التأكد من أنك لا تحتاجها.

## حالات البث

`STOPPED` و `STARTING` و `LIVE` و `RESTARTING` و `ERROR` محفوظة في MongoDB وتظهر في لوحة المالك.

## استكشاف الأخطاء

### البوت لا يبدأ

- تحقق من `BOT_TOKEN`, `OWNER_ID`, `API_ID`, `API_HASH`, `MONGO_URI`, و`CHANNEL_ID`.
- افحص `logs/bot.log` و`logs/errors.log`.
- تأكد من الوصول إلى MongoDB.

### FFmpeg يتوقف

- افحص `logs/ffmpeg.log`.
- تحقق من RTMP URL وStream Key من Telegram.
- جرّب تقليل `VIDEO_BITRATE` أو `RESOLUTION`.
- تأكد من أن البوت/الحساب لديه صلاحيات إدارة البث في القناة.

### البث يعمل لكن الصورة مشوهة

النظام يستخدم `scale`, `pad`, `fps`, و`format=yuv420p` للحفاظ على النسبة ومنع اختلافات الترميز بين الفيديوهات. إذا استمر العطل، جرّب `1280x720` و`FPS=30` ومعدل بث أقل.

### لا يمكن رفع الفيديو

- تأكد من وجود مساحة حرة.
- تحقق من تثبيت `ffprobe` وليس `ffmpeg` فقط.
- راجع `logs/bot.log` لمعرفة إن كان الخطأ من Telegram أو من فحص الملف.

## الأمان

- لا يتم وضع أي token أو API credential في الكود.
- `.env` وملفات Pyrogram session مستبعدة من Git.
- لا يتم تسجيل Bot Token أو API Hash أو Stream Key.
- كل Callback يتحقق من `OWNER_ID`.
- FFmpeg يُشغّل عبر `create_subprocess_exec` بقائمة arguments، ولا تُقبل أوامر FFmpeg من المستخدم.
- مسارات الملفات محمية من Path Traversal.
- لا يسمح النظام بتشغيل أكثر من عملية FFmpeg واحدة للبث نفسه.