from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, request_data, **kwargs):
        if not request_data["email"]:
            raise ValueError("Users must have an email.")
        if not request_data["name"]:
            raise ValueError("Users must have a name.")

        user = self.model(email=request_data["email"], name=request_data["name"])

        user.set_password(request_data["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, name, **extra_fields):
        request_data = {
            "email": email,
            "password": password,
            "name": name,
        }
        user = self.create_user(request_data)
        user.manager = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    email = models.EmailField(verbose_name="メールアドレス", max_length=255, unique=True)
    name = models.CharField(verbose_name="名前", max_length=20)
    active = models.BooleanField(verbose_name="有効フラグ", default=True)
    manager = models.BooleanField(verbose_name="管理者フラグ", default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.manager

    def has_module_perms(self, app_label):
        return self.manager

    @property
    def is_active(self):
        return self.active

    @property
    def is_manager(self):
        return self.manager

    @property
    def is_staff(self):
        return self.manager

    class Meta:
        db_table = "user"
        verbose_name = "ユーザー"
