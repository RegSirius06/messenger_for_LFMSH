import os
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from lfmsh.models import account, message, chat, chat_and_acc, chat_valid, announcement
from django.templatetags.static import static
from django.core.paginator import Paginator
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from PIL import Image
import datetime
import uuid

class ImageSelectWidget(forms.RadioSelect):
    def render(self, name, value, attrs=None, renderer=None):
        output = []
        for option_value, option_label in self.choices:
            image_path = f'images/{option_value}'  # Путь до изображения
            image_url = static(image_path)
            image_tag = format_html('<img src="{}" alt="{}" />', image_url, option_label)
            label_tag = format_html(
                '<label for="{}">{} {}</label>',
                attrs['id'], format_html('<input type="radio" name="{}" value="{}" />', name, option_value), image_tag
            )
            output.append(format_html('<div>{}</div>', label_tag))
        return mark_safe('\n'.join(output))

class SetStatus(forms.Form):
    status = forms.CharField(max_length=50, required=False, label="Введите новый статус:")

    def clean_status(self):
        return self.cleaned_data['status']

class SetReadStatusForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class NewMessageForm(forms.Form):
    message_text = forms.CharField(widget=forms.Textarea, help_text="Текст сообщения.", label="Текст:")

    def clean_message_text(self):
        return self.cleaned_data['message_text']

    message_anonim = forms.BooleanField(initial=False, required=False, label="Анонимно?", help_text="Если вы хотите отправить сообщение анонимно, вы должны поставить галочку.")

    def clean_message_anonim(self):
        return self.cleaned_data['message_anonim']
    
    class Meta:
        model = message
        fields = ['message_receiver', 'message_text', 'message_anonim']

class NewMessageForm_WithoutAnonim(forms.Form):
    message_text = forms.CharField(widget=forms.Textarea, help_text="Текст сообщения.", label="Текст:")

    def clean_message_text(self):
        return self.cleaned_data['message_text']
    
    class Meta:
        model = message
        fields = ['message_receiver', 'message_text', 'message_anonim']

class ReNewMessageFormAnonim(forms.Form):
    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['delete'] = forms.BooleanField(required=False, widget=forms.HiddenInput())

    message_text = forms.CharField(widget=forms.Textarea, help_text="Текст сообщения.", label="Текст:")

    def clean_message_text(self):
        return self.cleaned_data['message_text']

    message_anonim = forms.BooleanField(initial=False, required=False, label="Анонимно?", help_text="Если вы хотите отправить сообщение анонимно, вы должны поставить галочку.")

    def clean_message_anonim(self):
        return self.cleaned_data['message_anonim']
    
    class Meta:
        model = message
        fields = ['message_text', 'message_anonim']

class ReNewMessageFormBase(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delete'] = forms.BooleanField(required=False, widget=forms.HiddenInput())

    message_text = forms.CharField(widget=forms.Textarea, help_text="Текст сообщения.", label="Текст:")

    def clean_message_text(self):
        return self.cleaned_data['message_text']
    
    class Meta:
        model = message
        fields = ['message_text']

class NewChatForm(forms.Form):
    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super(NewChatForm, self).__init__(*args, **kwargs)
        if current_user is not None:
            self.fields['chat_members'].queryset = account.objects.exclude(pk=current_user.pk)

    chat_name = forms.CharField(label="Название чата:")

    def clean_chat_name(self):
        name = self.cleaned_data['chat_name']
        chat_all = [f'{i.name}' for i in chat.objects.all() if chat_valid.objects.get(what_chat=i).avaliable]
        if f'{name}' in chat_all: raise ValidationError(_('Чат с таким именем уже существует. Постарайтесь быть креативнее.'))
        return name
    
    chat_description = forms.CharField(label="Описание чата:")

    def clean_chat_description(self):
        return self.cleaned_data['chat_description']
    
    image_list = [f'{i}.png' for i in range(9)]
    image_choice = forms.ChoiceField(label="Аватарка чата:", required=False, choices=[(img, img) for img in image_list], widget=ImageSelectWidget())

    def clean_image_choice(self):
        img = self.cleaned_data['image_choice']
        if img is None: img = self.image_list[0]
        return img

    chat_anonim = forms.BooleanField(initial=False, required=False, help_text="Если вы хотите сделать чат анонимным, поставьте здесь галочку.\nЭтот параметр неизменяем.", label="Чат анонимный?")

    def clean_chat_anonim(self):
        return self.cleaned_data['chat_anonim']

    chat_anonim_legacy = forms.BooleanField(initial=False, required=False, label="Анонимные сообщения?", help_text="Если вы хотите разрешить отправку анонимных сообщений, вы должны поставить галочку.\nЭтот параметр неизменяем, не влияет на анонимный чат.")

    def clean_chat_anonim_legacy(self):
        return self.cleaned_data['chat_anonim_legacy']

    chat_members = forms.ModelMultipleChoiceField(queryset=account.objects.all(), label="Участники чата:", help_text="Выберите участника(-ов) чата.")

    def clean_chat_members(self):
        members = self.cleaned_data['chat_members']
        if len(list(members)) > 25:
            raise ValidationError(_('В чате не может быть больше 25-ти человек. Если вы хотите создать чат с большим количеством людей, вам нужно обратиться к администратору.'))
        return members

class NewChatFormConflict(forms.Form):
    CONFLICT_SOLVES = (
        (0, "Создать новый чат и заархивировать существующий"),
        (1, "Не создавать новый чат, заархивировать существующий"),
        (2, "Не создавать новый чат, не архивировать существующий"),
    )

    solve = forms.ChoiceField(choices=CONFLICT_SOLVES, label="Действие:")

    def clean_type_(self):
        return self.cleaned_data['solve']

class ReNewChatFormAnonim(forms.Form):
    def __init__(self, *args, **kwargs):
        current_users = kwargs.pop('current_users', None)
        current_user = kwargs.pop('current_user', None)
        super(ReNewChatFormAnonim, self).__init__(*args, **kwargs)
        if current_users is not None:
            current_users_pk = [i.pk for i in current_users]
            self.fields['chat_creator'].queryset = account.objects.filter(pk__in=current_users_pk)
            if current_user is not None: self.fields['chat_creator'].queryset = account.objects.filter(pk__in=current_users_pk).exclude(pk=current_user.pk)
        self.fields['delete'] = forms.BooleanField(required=False, widget=forms.HiddenInput())

    chat_creator = forms.ModelChoiceField(queryset=account.objects.all(), required=False, label="Создатель:", help_text="Здесь вы можете изменить создателя чата. Это необязательно.")

    def clean_chat_creator(self):
        return self.cleaned_data['chat_creator']

    image_list = [f'{i}.png' for i in range(9)]
    image_choice = forms.ChoiceField(label="Аватарка чата:", choices=[(img, img) for img in image_list], widget=ImageSelectWidget())

    def clean_image_choice(self):
        return self.cleaned_data['image_choice']

    chat_name = forms.CharField(label="Название чата:")

    def clean_chat_name(self):
        name = self.cleaned_data['chat_name']
        #chat_all = [f'{i.name}' for i in chat.objects.all() if chat_valid.objects.get(what_chat=i).avaliable]
        #if f'{name}' in chat_all: raise ValidationError(_('Чат с таким именем уже существует. Постарайтесь быть креативнее.'))
        return name

    chat_text = forms.CharField(widget=forms.Textarea, label="Описание чата:")

    def clean_chat_text(self):
        return self.cleaned_data['chat_text']

    chat_anonim = forms.BooleanField(required=False, label="Анонимные сообщения?", help_text="Если вы хотите разрешить отправку сообщения анонимно, вы должны поставить галочку.")

    def clean_message_anonim(self):
        return self.cleaned_data['chat_anonim']

class ReNewChatFormBase(forms.Form):
    def __init__(self, *args, **kwargs):
        current_users = kwargs.pop('current_users', None)
        current_user = kwargs.pop('current_user', None)
        super(ReNewChatFormBase, self).__init__(*args, **kwargs)
        if current_users is not None:
            current_users_pk = [i.pk for i in current_users]
            self.fields['chat_creator'].queryset = account.objects.filter(pk__in=current_users_pk)
            if current_user is not None: self.fields['chat_creator'].queryset = account.objects.filter(pk__in=current_users_pk).exclude(pk=current_user.pk)
        self.fields['delete'] = forms.BooleanField(required=False, widget=forms.HiddenInput())

    chat_creator = forms.ModelChoiceField(queryset=account.objects.all(), required=False, label="Создатель:", help_text="Здесь вы можете изменить создателя чата. Это необязательно.")

    def clean_chat_creator(self):
        return self.cleaned_data['chat_creator']

    image_list = [f'{i}.png' for i in range(9)]
    image_choice = forms.ChoiceField(label="Аватарка чата:", choices=[(img, img) for img in image_list], widget=ImageSelectWidget())

    def clean_image_choice(self):
        return self.cleaned_data['image_choice']

    chat_name = forms.CharField(label="Название чата:")

    def clean_chat_name(self):
        name = self.cleaned_data['chat_name']
        #chat_all = [f'{i.name}' for i in chat.objects.all() if chat_valid.objects.get(what_chat=i).avaliable]
        #if f'{name}' in chat_all: raise ValidationError(_('Чат с таким именем уже существует. Постарайтесь быть креативнее.'))
        return name

    chat_text = forms.CharField(widget=forms.Textarea, label="Описание чата:")

    def clean_chat_text(self):
        return self.cleaned_data['chat_text']

class NewAccountForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['save_and_new'] = forms.BooleanField(required=False, widget=forms.HiddenInput())

    EXISTING_TYPES = (
        (0, "Пионер"),
        (1, "Педсостав"),
    )

    type_ = forms.ChoiceField(choices=EXISTING_TYPES, label="Тип аккаунта:")

    def clean_type_(self):
        return self.cleaned_data['type_']

    first_name = forms.CharField(label="Имя:")

    def clean_first_name(self):
        return self.cleaned_data['first_name']
    
    middle_name = forms.CharField(label="Отчество:")

    def clean_middle_name(self):
        return self.cleaned_data['middle_name']
    
    last_name = forms.CharField(label="Фамилия:")

    def clean_last_name(self):
        return self.cleaned_data['last_name']

    party = forms.IntegerField(label="Номер отряда:")

    def clean_party(self):
        return self.cleaned_data['party']

class NewAccountFullForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['save_and_new'] = forms.BooleanField(required=False, widget=forms.HiddenInput())

    EXISTING_TYPES = (
        (0, "Пионер"),
        (1, "Педсостав"),
    )

    type_ = forms.ChoiceField(choices=EXISTING_TYPES, label="Тип аккаунта:")

    def clean_type_(self):
        return self.cleaned_data['type_']

    first_name = forms.CharField(label="Имя:")

    def clean_first_name(self):
        return self.cleaned_data['first_name']
    
    middle_name = forms.CharField(label="Отчество:")

    def clean_middle_name(self):
        return self.cleaned_data['middle_name']
    
    last_name = forms.CharField(label="Фамилия:")

    def clean_last_name(self):
        return self.cleaned_data['last_name']
    
    username = forms.CharField(label="Login:")

    def clean_username(self):
        return self.cleaned_data['username']
    
    password = forms.CharField(label="Password:")

    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password) != 8 and len(password) != 12:
            raise ValidationError(_('Длина пароля должна быть равной 8-ми символам для пионера и 12-ти символам для педагога.'))
        return password

    party = forms.IntegerField(label="Номер отряда:")

    def clean_party(self):
        return self.cleaned_data['party']

class ReNewAccountForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delete'] = forms.BooleanField(required=False, widget=forms.HiddenInput())

    first_name = forms.CharField(label="Имя:")

    def clean_first_name(self):
        return self.cleaned_data['first_name']
    
    middle_name = forms.CharField(label="Отчество:")

    def clean_middle_name(self):
        return self.cleaned_data['middle_name']
    
    last_name = forms.CharField(label="Фамилия:")

    def clean_last_name(self):
        return self.cleaned_data['last_name']

    username = forms.CharField(label="Login:")

    def clean_username(self):
        return self.cleaned_data['username']

    party = forms.IntegerField(label="Номер отряда:")

    def clean_party(self):
        return self.cleaned_data['party']

class NewAnnouncementForm(forms.Form):
    name = forms.CharField(max_length=50, label="Название:")

    def clean_name(self):
        return self.cleaned_data["name"]

    text = forms.CharField(label="Текст:", max_length=5000, widget=forms.Textarea)

    def clean_text(self):
        return self.cleaned_data["text"]

    picture = forms.ImageField(label="Картинка:", widget=forms.ClearableFileInput, required=False)

    def clean_picture(self):
        picture = self.cleaned_data["picture"]
        if picture:
            if not picture.name.endswith((".png", ".jpg")):
                raise ValidationError(_("Допустимые расширения файлов: .png, .jpg"))
        return picture

class NewAnnouncementFullForm(forms.Form):
    name = forms.CharField(max_length=50, label="Название:")

    def clean_name(self):
        return self.cleaned_data["name"]

    creator = forms.ModelChoiceField(queryset=account.objects.all(), label="Создатель:")

    def clean_creator(self):
        return self.cleaned_data["creator"]

    text = forms.CharField(label="Текст:", max_length=5000, widget=forms.Textarea)

    def clean_text(self):
        return self.cleaned_data["text"]
    
    picture = forms.ImageField(label="Картинка:", required=False)

    def clean_picture(self):
        picture = self.cleaned_data["picture"]
        if picture:
            max_size = 15 * 1024 * 1024
            if picture.size > max_size:
                raise ValidationError(_(f"Максимальный размер файла - {max_size/1024/1024}MB"))
        return picture

    type_ = forms.ChoiceField(required=False, choices=announcement.PICTURE_TYPES, label="Ориентации картинки:", help_text="По-умолчанию горизонтально.")

    def clean_type_(self):
        x = self.cleaned_data['type_']
        return int(x) if x else 0

class ReNewAnnouncementForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delete'] = forms.BooleanField(required=False, widget=forms.HiddenInput())
    
    status = forms.BooleanField(label="Объявление принято?", required=False)

    def clean_name(self):
        return self.cleaned_data["status"]

    creator = forms.ModelChoiceField(queryset=account.objects.all(), label="Создатель:")

    def clean_creator(self):
        return self.cleaned_data["creator"]
