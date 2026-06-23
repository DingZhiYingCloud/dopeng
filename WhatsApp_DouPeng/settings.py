import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# 跨域设置
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# 跨域请求配置，允许所有源的跨域请求
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = True

# 允许使用标签内嵌页面
X_FRAME_OPTIONS = 'ALLOWALL'

# Referrer-Policy 策略：跨域跳转时携带 origin 作为 Referer（匹配浏览器默认行为）
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders', # 跨域请求中间件
    'XingXingWeb.apps.XingxingwebConfig', # Web前端层
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # 跨域请求中间件
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'XingXingWeb.middleware.RequestLogMiddleware',  # 请求访问日志
]

ROOT_URLCONF = 'WhatsApp_DouPeng.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'XingXingWeb' / 'templates',  # Web前端模板目录
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'WhatsApp_DouPeng.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'zh-hans' # 中文简体

TIME_ZONE = 'Asia/Shanghai' # 上海时间

USE_I18N = True # 开启国际化

USE_TZ = True # 开启时区支持

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    BASE_DIR / 'XingXingWeb' / 'static',  # Web前端静态文件
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 主域名
MAIN_DOMAIN = os.getenv('MAIN_DOMAIN', 'domain.com')

# 斗篷开关：False 时关闭斗篷分流，所有请求直接渲染模板
CLOAK_ENABLED = os.getenv('CLOAK_ENABLED', 'True').lower() in ('true', '1', 'yes')

# 流量分析域名：搜索引擎中文真人请求 302 跳转目标
GA_DOMAIN_NAME = os.getenv('GA_DOMAIN_NAME', '')

