# 勤怠管理システム

## システム構成図
![INFRA STRUCTURE IMAGE](infra_structure.png)

## 全体の構成
![WEB SERVICE](web_service.png)

## 開発環境構築手順

DBを作成する。

```bash
> createdb -U postgres -E UTF-8 attendance_management_system
> psql -U postgres -l
```

## .env

`SECRET_KEY`は以下の手順で環境ごとに異なる値を設定する。

```bash
$ python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> get_random_secret_key()
'SECRET_KEYが出力される'