from django.shortcuts import redirect, render
from lfmsh.models import account, message, chat, chat_valid, chat_and_acc, announcement
from django.views import generic
from django.contrib.auth.models import User, Group, Permission, AnonymousUser
from django.contrib.auth.hashers import make_password
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from lfmsh.forms import NewMessageForm, NewAccountForm, ReNewMessageFormAnonim, ReNewMessageFormBase, NewChatForm,\
    NewMessageForm_WithoutAnonim, ReNewChatFormAnonim, ReNewChatFormBase, SetStatus,  SetReadStatusForm, NewChatFormConflict,\
            NewAccountFullForm, ReNewAccountForm, NewAnnouncementForm, NewAnnouncementFullForm, ReNewAnnouncementForm
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import permission_required, login_required
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.db.models import Q, Subquery
import datetime
import random
import string
import uuid
import os

def index(request):
    anns = announcement.objects.filter(status=True)
    paginator1 = Paginator(anns, 3)
    page1 = request.GET.get('page1')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    readen_status = True
    if request.user.is_authenticated:
        for i in list(chat_and_acc.objects.filter(what_acc=request.user.account)):
            readen_status &= i.readen
    return render(
        request,
        'index.html',
        context={'readen_status': readen_status, 'ant_list': items1,},
    )

@permission_required('lfmsh.staff_')
@permission_required('lfmsh.ant_edit')
def plan_x(request):
    anns = announcement.objects.filter(status=False)#.order_by("creator", "name")
    paginator1 = Paginator(anns, 25)
    page1 = request.GET.get('page1')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    return render(
        request,
        'messenger/plan.html',
        context={'plans': items1,},
    )

def update_chats(request):
    chat_valid_all = list(chat_valid.objects.exclude(avaliable=False))
    list_id_chats = []
    for i in chat_valid_all:
        if i.getting_access(request.user.account):
            list_id_chats.append(i.what_chat.id)
    mess_pr = chat.objects.filter(id__in=list_id_chats)
    chat_and_acc_all = chat_and_acc.objects.filter(what_chat__in=mess_pr).filter(what_acc=request.user.account)
    paginator1 = Paginator(mess_pr, 25)
    page1 = request.GET.get('page1')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)

    html = render_to_string('messenger/update_chats.html', {'items1': items1, 'readen_status': chat_and_acc_all})
    return JsonResponse({'html': html})

def update_globals(request):
    mess_pub = message.objects.filter(receiver=None)
    paginator2 = Paginator(mess_pub, 10)
    page2 = request.GET.get('page2')
    try:
        items2 = paginator2.page(page2)
    except PageNotAnInteger:
        items2 = paginator2.page(1)
    except EmptyPage:
        items2 = paginator2.page(paginator2.num_pages)

    html = render_to_string('messenger/update_globals.html', {'items2': items2})
    return JsonResponse({'html': html})

@login_required
def home(request):
    chat_valid_all = list(chat_valid.objects.exclude(avaliable=False))
    list_id_chats = []
    for i in chat_valid_all:
        if i.getting_access(request.user.account):
            list_id_chats.append(i.what_chat.id)
    mess_pr = chat.objects.filter(id__in=list_id_chats)
    chat_and_acc_all = chat_and_acc.objects.filter(what_chat__in=mess_pr).filter(what_acc=request.user.account)
    mess_pub = message.objects.filter(receiver=None)
    paginator1 = Paginator(mess_pr, 1)
    paginator2 = Paginator(mess_pub, 10)
    page1 = request.GET.get('page1')
    page2 = request.GET.get('page2')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    try:
        items2 = paginator2.page(page2)
    except PageNotAnInteger:
        items2 = paginator2.page(1)
    except EmptyPage:
        items2 = paginator2.page(paginator2.num_pages)
    if request.method == 'POST':
        form = SetStatus(request.POST)
        if form.is_valid():
            account_ = account.objects.get(id=request.user.account.id)
            new_status = form.cleaned_data['status']
            account_.account_status = new_status
            account_.save()
            return redirect('messages')
    else:
        status = request.user.account.account_status
        form = SetStatus(initial={'status': status,})
    context={'messages': mess_pr, 'messages_public': mess_pub, 'items1': items1, 'items2': items2, 'form': form, 'readen_status': chat_and_acc_all,}
    return render(
        request,
        'messenger/messages.html',
        context=context,
    )

@login_required
def home_send(request):
    mess_pr = message.objects.filter(creator=request.user.account).exclude(receiver=None)
    mess_pr_ = message.objects.filter(creator=request.user.account).exclude(receiver=None)
    if list(mess_pr) != []:
        print(mess_pr)
        i = 0
        while True:
            if not chat_valid.objects.get(what_chat=mess_pr[i].receiver).avaliable:
                mess_pr = mess_pr.exclude(id=mess_pr[i].id)
                i -= 1
            i += 1
            if i >= len(mess_pr): break
    if list(mess_pr_) != []:
        i = 0
        while True:
            if chat_valid.objects.get(what_chat=mess_pr_[i].receiver).avaliable:
                mess_pr_ = mess_pr_.exclude(id=mess_pr_[i].id)
                i -= 1
            i += 1
            if i >= len(mess_pr_): break
    mess_pub = message.objects.filter(creator=request.user.account).filter(receiver=None)
    paginator1 = Paginator(mess_pr, 25)
    paginator2 = Paginator(mess_pub, 25)
    paginator3 = Paginator(mess_pr_, 25)
    page1 = request.GET.get('page1')
    page2 = request.GET.get('page2')
    page3 = request.GET.get('page2')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    try:
        items2 = paginator2.page(page2)
    except PageNotAnInteger:
        items2 = paginator2.page(1)
    except EmptyPage:
        items2 = paginator2.page(paginator2.num_pages)
    try:
        items3 = paginator3.page(page3)
    except PageNotAnInteger:
        items3 = paginator3.page(1)
    except EmptyPage:
        items3 = paginator3.page(paginator3.num_pages)
    return render(
        request,
        'messenger/messages_list.html',
        context={'messages': mess_pr, 'messages_public': mess_pub,
                 'items1': items1, 'items2': items2, 'items3': items3,},
    )

@permission_required('lfmsh.staff_')
@permission_required('lfmsh.edit_users')
def account_info(request):
    acc_all = account.objects.all()
    paginator1 = Paginator(acc_all, 25)
    page1 = request.GET.get('page1')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    return render(
        request,
        'messenger/account_status.html',
        context={
            'object_list': items1,
        }
    )

@permission_required('lfmsh.staff_')
@permission_required('lfmsh.register')
def new_account_add(request):
    def translit(s: str) -> str:
        ans = ""
        s = s.lower()
        table_d = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'ye', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y',
                   'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', ' ': '_',
                   'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '', 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}
        for c in s:
            try: ans += table_d[c]
            except KeyError: ans += c
        return ans

    def gen_pass(length: int) -> str:
        lang = []
        hard_to_read = "l1IioO0"
        for i in string.printable[:62]:
            if i in hard_to_read: continue
            lang.append(i)
        list_ = []
        for u in User.objects.all():
            list_.append(u.password)
        set_list = set(list_)
        while True:
            pas = ""
            for i in range(length):
                el = random.choice(lang)
                pas += el
            if pas not in set_list:
                return pas

    if request.method == 'POST':
        form = NewAccountForm(request.POST)
        if form.is_valid():
            new_account = account()

            type_ = form.cleaned_data['type_']
            first_name = form.cleaned_data['first_name']
            middle_name = form.cleaned_data['middle_name']
            last_name = form.cleaned_data['last_name']
            username = f'{translit(first_name[0])}.{translit(middle_name[0])}.{translit(last_name)}'
            for u in User.objects.all():
                if f'{u.username}' == f'{username}': return HttpResponse("<h2>Такой пользователь уже существует. <a href=\"/\">Назад...</a></h2>")
            party = form.cleaned_data['party']
            len_pass = 8 if type_ == 0 else 12
            password = gen_pass(len_pass)

            if f'{type_}' == '1':
                group_, created = Group.objects.get_or_create(name="pedagogue")
                if created:
                    perms, created = Permission.objects.get_or_create(codename="staff_")
                    group_.permissions.add(perms)
                    perms, created = Permission.objects.get_or_create(codename="ant_edit")
                    group_.permissions.add(perms)
                    perms, created = Permission.objects.get_or_create(codename="edit_users")
                    group_.permissions.add(perms)
            else: group_, created = Group.objects.get_or_create(name="listener")
            group_.save()
            
            new_user = User.objects.create(username=username, password=make_password(password))
            new_user.groups.add(group_)

            new_account.id = uuid.uuid4()
            new_account.user = new_user
            new_account.first_name = first_name
            new_account.middle_name = middle_name
            new_account.last_name = last_name
            new_account.party = party
            new_account.save()

            s_write = f'login: {username}\npassword: {password}\n' + '-' * 30 + '\n'
            f = open("All_users.txt", "a")
            f.write(s_write)
            f.close()

            if form.cleaned_data['save_and_new']:
                return redirect('new-user')
            else:
                return redirect('info-users')
    else:
        type_ = 0
        first_name = "Not stated"
        middle_name = "Not stated"
        last_name = "Not stated"
        party = 0
        form = NewAccountForm(initial={'type_': type_, 'first_name': first_name, 'middle_name': middle_name, 'last_name': last_name, 'party': party})
    return render(request, 'messenger/account_form.html', {'form': form,})

@permission_required('lfmsh.staff_')
@permission_required('lfmsh.register')
def new_account_full_add(request):
    def translit(s: str) -> str:
        ans = ""
        s = s.lower()
        table_d = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'ye', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y',
                   'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', ' ': '_',
                   'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '', 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}
        for c in s:
            try: ans += table_d[c]
            except KeyError: ans += c
        return ans

    if request.method == 'POST':
        form = NewAccountFullForm(request.POST)
        if form.is_valid():
            new_account = account()

            type_ = form.cleaned_data['type_']
            first_name = form.cleaned_data['first_name']
            middle_name = form.cleaned_data['middle_name']
            last_name = form.cleaned_data['last_name']
            username = translit(form.cleaned_data['username'])
            for u in User.objects.all():
                if f'{u.username}' == f'{username}': return HttpResponse("<h2>Такой пользователь уже существует. <a href=\"/\">Назад...</a></h2>")
            party = form.cleaned_data['party']
            password = form.cleaned_data['password']

            if f'{type_}' == '1':
                group_, created = Group.objects.get_or_create(name="pedagogue")
                if created:
                    perms, created = Permission.objects.get_or_create(codename="staff_")
                    group_.permissions.add(perms)
                    perms, created = Permission.objects.get_or_create(codename="ant_edit")
                    group_.permissions.add(perms)
                    perms, created = Permission.objects.get_or_create(codename="edit_users")
                    group_.permissions.add(perms)
            else: group_, created = Group.objects.get_or_create(name="listener")
            group_.save()
            
            new_user = User.objects.create(username=username, password=make_password(password))
            new_user.groups.add(group_)

            new_account.id = uuid.uuid4()
            new_account.user = new_user
            new_account.first_name = first_name
            new_account.middle_name = middle_name
            new_account.last_name = last_name
            new_account.party = party
            new_account.save()

            s_write = f'login: {username}\npassword: {password}\n' + '-' * 30 + '\n'
            f = open("All_users.txt", "a")
            f.write(s_write)
            f.close()

            if form.cleaned_data['save_and_new']:
                return redirect('new-user')
            else:
                return redirect('info-users')
    else:
        type_ = 0
        first_name = "Not stated"
        middle_name = "Not stated"
        last_name = "Not stated"
        party = 0
        form = NewAccountFullForm(initial={'type_': type_, 'first_name': first_name, 'middle_name': middle_name, 'last_name': last_name, 'party': party})
    return render(request, 'messenger/account_form.html', {'form': form,})

@permission_required('lfmsh.staff_')
@permission_required('lfmsh.edit_users')
def re_new_account_full_add(request, pk):
    def translit(s: str) -> str:
        ans = ""
        s = s.lower()
        table_d = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'ye', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y',
                   'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', ' ': '_',
                   'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '', 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}
        for c in s:
            try: ans += table_d[c]
            except KeyError: ans += c
        return ans

    account_ = get_object_or_404(account, id=pk)
    user_ = User.objects.get(id=account_.user.id)
    if request.method == 'POST':
        form = ReNewAccountForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['delete']:
                account_.delete()
                user_.delete()
            else:
                first_name = form.cleaned_data['first_name']
                middle_name = form.cleaned_data['middle_name']
                last_name = form.cleaned_data['last_name']
                username = translit(form.cleaned_data['username'])
                for u in User.objects.all():
                    if f'{u.username}' == f'{username}': return HttpResponse("<h2>Такой пользователь уже существует. <a href=\"/\">Назад...</a></h2>")
                party = form.cleaned_data['party']
                
                user_.username = username
                user_.save()

                account_.first_name = first_name
                account_.middle_name = middle_name
                account_.last_name = last_name
                account_.party = party
                account_.save()
            return redirect('info-users')
    else:
        first_name = account_.first_name
        middle_name = account_.middle_name
        last_name = account_.last_name
        party = account_.party
        username = user_.username
        form = ReNewAccountForm(initial={'first_name': first_name, 'middle_name': middle_name, 'last_name': last_name, 'party': party, 'username': username,})
    return render(request, 'messenger/form_edit_for_all.html', {'form': form, 'delta': 'аккаунта'})

@login_required
def new_message_add(request):
    if request.method == 'POST':
        form = NewMessageForm(request.POST)
        if form.is_valid():
            new_message = message()
            new_message.id = uuid.uuid4()
            new_message.date = datetime.datetime.today()
            new_message.time = datetime.datetime.now()
            new_message.creator = request.user.account
            new_message.receiver = None
            new_message.text = form.cleaned_data['message_text']
            new_message.anonim = form.cleaned_data['message_anonim']
            #if new_message.creator == new_message.receiver:
            #    return HttpResponse("<h2>Неужели вы <em>настолько</em> одиноки?..<br/>К сожалению, нельзя себе отправлять сообщения.<a href=\"/\">Назад...</a></h2>")
            new_message.save()
            return redirect('messages')
    else:
        form = NewMessageForm(initial={'message_text': '',})

    return render(request, 'messenger/messages_new.html', {'form': form,})

@login_required
def new_chat_add(request):
    def make_valid_form(chat_: chat, chat_valid_: chat_valid):
        return f'{chat_valid_.list_members}{chat_.anonim}' if chat_valid_.avaliable else 'None'
    current_user = request.user.account
    if request.method == 'POST':
        form = NewChatForm(request.POST, current_user=current_user)
        if form.is_valid():
            new_message = message()
            new_chat = chat()
            new_chat_valid = chat_valid()

            new_chat.id = uuid.uuid4()
            new_chat.anonim = form.cleaned_data["chat_anonim"]
            new_chat.anonim_legacy = form.cleaned_data["chat_anonim_legacy"]
            new_chat.name = form.cleaned_data["chat_name"]
            new_chat.description = form.cleaned_data["chat_description"]
            members = list(f'{i.id}' for i in form.cleaned_data["chat_members"])
            members.append(f'{request.user.account.id}')
            new_chat.chat_ico = form.cleaned_data["image_choice"]
            new_chat.creator = request.user.account
            new_chat.cnt = len(members)
            
            new_message.id = uuid.uuid4()
            new_message.date = datetime.datetime.today()
            new_message.time = datetime.datetime.now()
            new_message.creator = request.user.account
            new_message.receiver = new_chat
            new_message.text = f'Создан чат {new_chat.name} ({new_chat.description}).'
            new_message.anonim = True
            
            new_chat_valid.id = uuid.uuid4()
            new_chat_valid.what_chat = new_chat
            new_chat_valid.avaliable = True
            new_chat_valid.list_members = members
            new_chat_valid.list_messages.append(f'{new_message.id}')
            members = list(form.cleaned_data["chat_members"])
            members.append(request.user.account)

            set_of_chats_valid = list(chat_valid.objects.filter(avaliable=True))

            new_chat.save()
            new_message.save()
            new_chat_valid.save()

            for acc in members: chat_and_acc.objects.create(id = uuid.uuid4(), what_chat = new_chat, what_acc = acc, readen = False)

            for i in range(len(set_of_chats_valid)):
                if make_valid_form(new_chat, new_chat_valid) == make_valid_form(set_of_chats_valid[i].what_chat, set_of_chats_valid[i]):
                    #return HttpResponse("<h2>Уже сейчас подобный чат существует. Надо только покопаться... не в архиве. <a href=\"/\">Назад...<a/></h2>")
                    return redirect('chats-new-conflict', new_chat.id, new_message.id, new_chat_valid.id, set_of_chats_valid[i].what_chat.id)

            return redirect('messages')
    else:
        form = NewChatForm(current_user=current_user)

    return render(request, 'messenger/chats_new.html', {'form': form,})

@login_required
def new_chat_add_confilct(request, new_chat_id, new_message_id, new_chat_valid_id, existing_chat_id):
    new_chat = chat.objects.get(id=new_chat_id)
    new_message = message.objects.get(id=new_message_id)
    new_chat_valid = chat_valid.objects.get(id=new_chat_valid_id)
    existing_chat = chat.objects.get(id=existing_chat_id)
    existing_chat.archive()
    if request.method == 'POST':
        form = NewChatFormConflict(request.POST)
        if form.is_valid():
            solve = int(form.cleaned_data['solve'])
            
            if solve == 2:
                new_chat_valid.delete()
                new_message.delete()
                new_chat.delete()
                existing_chat.dearchive()
                return redirect('messages')
            
            if solve == 1:
                new_chat_valid.delete()
                new_message.delete()
                new_chat.delete()
                return redirect('messages')

            if solve == 0:
                pass

            return redirect('messages')
    else:
        form = NewChatFormConflict()

    return render(request, 'messenger/chats_new_conflict.html', {'form': form,})

def update_msgs(request, pk):
    chat_ = get_object_or_404(chat, pk=pk)
    chat_valid_ = chat_valid.objects.get(what_chat=chat_)
    chat_and_acc_all_ = chat_valid_.get_all_CAA()
    chat_and_acc_ = chat_and_acc_all_.get(what_acc=request.user.account)
    message_all_ = chat_valid_.get_all_msg()
    paginator1 = Paginator(message_all_, 20)
    page1 = request.GET.get('page2')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)

    html = render_to_string('messenger/messages_list_n.html', {'messages': items1})
    return JsonResponse({'html': html, 'CAA': chat_and_acc_.readen})

@login_required
def chat_view(request, pk):
    chat_ = get_object_or_404(chat, pk=pk)
    chat_valid_ = chat_valid.objects.get(what_chat=chat_)
    chat_and_acc_all_ = chat_valid_.get_all_CAA()
    chat_and_acc_ = chat_and_acc_all_.get(what_acc=request.user.account)
    chat_and_acc_.readen = True
    chat_and_acc_.save()
    message_all_ = chat_valid_.get_all_msg()
    paginator1 = Paginator(message_all_, 20)
    page1 = request.GET.get('page1')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    len_mess = 2000
    if request.method == 'POST':
        form = NewMessageForm_WithoutAnonim(request.POST) if chat_.anonim or not chat_.anonim_legacy else NewMessageForm(request.POST)
        form2 = SetReadStatusForm(request.POST)
        if form.is_valid():
            if len(list(chat_valid_.list_messages)) >= len_mess:
                redirect('messages')
            message_ = message()
            message_.id = uuid.uuid4()
            message_.date = datetime.datetime.today()
            message_.time = datetime.datetime.today()
            message_.creator = request.user.account
            message_.receiver = chat_
            message_.anonim_legacy = chat_.anonim
            message_.text = form.cleaned_data['message_text']
            if chat_.anonim_legacy: message_.anonim = form.cleaned_data['message_anonim']
            else: message_.anonim = chat_.anonim
            message_.save()
            chat_valid_.add_msg(message_)
            if len(list(chat_valid_.list_messages)) >= len_mess:
                last_message = message()
                last_message.id = uuid.uuid4()
                last_message.date = datetime.datetime.today()
                last_message.time = datetime.datetime.today()
                last_message.creator = chat_.creator
                last_message.receiver = chat_
                last_message.anonim_legacy = chat_.anonim
                last_message.text = f'В чате накопилось 2000 сообщений, поэтому он будет заархивирован.\n\nДля вашего удобства будет создан новый подобный чат.'
                last_message.anonim = True
                last_message.save()
                chat_valid_.add_msg(last_message)
                
                new_message = message()
                new_chat = chat()
                new_chat_valid = chat_valid()

                new_chat.id = uuid.uuid4()
                new_chat.anonim = chat_.anonim
                new_chat.anonim_legacy = chat_.anonim_legacy
                new_chat.name = chat_.name
                new_chat.description = chat_.description
                new_chat.creator = chat_.creator
                new_chat.cnt = chat_.cnt
                
                new_message.id = uuid.uuid4()
                new_message.date = datetime.datetime.today()
                new_message.time = datetime.datetime.now()
                new_message.creator = chat_.creator
                new_message.receiver = new_chat
                new_message.text = f'В предыдущем чате был достигнут лимит по количеству сообщений.\n\nВместо него создан аналогичный чат \"{new_chat.name} ({new_chat.description}).\"'
                new_message.anonim = True
                
                new_chat_valid.id = uuid.uuid4()
                new_chat_valid.what_chat = new_chat
                new_chat_valid.avaliable = True
                new_chat_valid.list_members = list(chat_valid_.list_members)
                new_chat_valid.list_messages = []
                new_chat_valid.list_messages.append(f'{new_message.id}')
                members = list(account.objects.filter(id__in=list(chat_valid_.list_members)))

                new_chat.save()
                new_message.save()
                new_chat_valid.save()
                chat_.archive()
                
                for acc in members: chat_and_acc.objects.create(id = uuid.uuid4(), what_chat = new_chat, what_acc = acc, readen = False)

                return redirect(new_chat.get_absolute_url())
            return redirect(chat_.get_absolute_url())
        if form2.is_valid():
            if chat_and_acc_.readen:
                chat_and_acc_.unread_chat()
                return redirect('messages')
            else:
                chat_and_acc_.read_chat()
            return redirect(chat_.get_absolute_url())
    else:
        form2 = SetReadStatusForm()
        anonim = False
        text = ''
        form = NewMessageForm(initial={'message_text': text, 'message_anonim': anonim,}) \
            if not chat_.anonim and chat_.anonim_legacy else NewMessageForm_WithoutAnonim(initial={'message_text': text})

    return render(request, 'messenger/chats_view_n.html', {'form': form, 'chat': chat_,
                                                           'form2': form2, 'readen_status': chat_and_acc_.readen,})

@login_required
def chat_archived_view(request, pk):
    chat_ = get_object_or_404(chat, pk=pk)
    chat_valid_ = chat_valid.objects.get(what_chat=chat_)
    #chat_and_acc_all_ = chat_valid_.get_all_CAA()
    message_all_ = chat_valid_.get_all_msg()
    paginator1 = Paginator(message_all_, 220)
    page1 = request.GET.get('page1')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    return render(request, 'messenger/chats_archived_view_n.html', {'messages': items1, 'chat': chat_,})

@login_required
def chat_archive(request):
    chat_valid_ = chat_valid.objects.exclude(avaliable=True)
    message_all_ = [i.what_chat for i in chat_valid_]
    paginator1 = Paginator(message_all_, 25)
    page1 = request.GET.get('page1')
    try:
        items1 = paginator1.page(page1)
    except PageNotAnInteger:
        items1 = paginator1.page(1)
    except EmptyPage:
        items1 = paginator1.page(paginator1.num_pages)
    return render(request, 'messenger/chat_archive.html', {'messages': items1,})

@login_required
def re_new_message_add(request, pk):
    message_ = get_object_or_404(message, pk=pk)
    x = chat_valid.objects.get(what_chat=message_.receiver) if message_.receiver is not None else None
    flag = x is not None
    if not flag: flag = message_.receiver is None
    else: flag = x.avaliable
    if flag:
        if message_.creator == request.user.account:
            anon_prov = message_.anonim and not message_.anonim_legacy

            if request.method == 'POST':
                form = ReNewMessageFormAnonim(request.POST) if anon_prov else ReNewMessageFormBase(request.POST)
                if form.is_valid():
                    if form.cleaned_data['delete']:
                        if message_.receiver is not None:
                            chat_valid_ = chat_valid.objects.get(what_chat=message_.receiver)
                            for i in range(len(chat_valid_.list_messages)):
                                if f'{chat_valid_.list_messages[i]}' == f'{message_.id}':
                                    del chat_valid_.list_messages[i]
                                    break
                        message_.delete()
                    else:
                        message_.text = form.cleaned_data['message_text'] + f"\n\n(Изменено {datetime.date.today()} в {datetime.time(hour=datetime.datetime.now().hour, minute=datetime.datetime.now().minute, second=datetime.datetime.now().second)})"
                        if anon_prov: message_.anonim = form.cleaned_data['message_anonim']
                        message_.save()
                    return redirect('messages-edit')
            else:
                anonim = message_.anonim
                text = f'{message_.text}'
                text = text[:-34] if text[-1] == ')' and "\n\n(Изменено " in text else text
                form = ReNewMessageFormAnonim(initial={'message_text': text, 'message_anonim': anonim,}) \
                    if anon_prov else ReNewMessageFormBase(initial={'message_text': text})

            return render(request, 'messenger/messages_edit_n.html', {'form': form,})
        else: return HttpResponse("<h2>Я, конечно, всё понимаю, но <em>этого</em> мне не понять...<br/>К сожалению, вы можете редактировать только свои сообщения. <a href=\"/\">Назад...</a></h2>")
    else: return HttpResponse("<h2>Чат с данным сообщением заархивирован. <a href=\"/\">Назад...<a/></h2>")

@login_required
def re_new_chat_add(request, pk):
    chat_ = get_object_or_404(chat, pk=pk)
    chat_valid_ = chat_valid.objects.get(what_chat=chat_)
    if chat_.creator == request.user.account:
        anon_prov = not chat_.anonim and not chat_.anonim_legacy
        current_users = account.objects.filter(id__in=[uuid.UUID(i) for i in chat_valid_.list_members])
        if request.method == 'POST':
            form = ReNewChatFormAnonim(request.POST, current_users=current_users, current_user=request.user.account)\
                   if anon_prov else ReNewChatFormBase(request.POST, current_users=current_users, current_user=request.user.account)
            if form.is_valid():
                chat_.name = form.cleaned_data['chat_name']
                chat_.description = form.cleaned_data['chat_text']
                if anon_prov: chat_.anonim_legacy = form.cleaned_data['chat_anonim']
                creator_chat = form.cleaned_data['chat_creator']
                chat_.chat_ico = form.cleaned_data["image_choice"]
                if creator_chat is not None: chat_.creator = creator_chat
                chat_.save()
                if form.cleaned_data['delete']:
                    chat_.archive()
                    return redirect('messages')
                return redirect(chat_.get_absolute_url())
        else:
            anonim = chat_.anonim_legacy
            name = chat_.name
            text = chat_.description
            chat_ico = chat_.chat_ico
            form = ReNewChatFormAnonim(initial={'chat_text': text, 'chat_name': name, 'chat_anonim': anonim, 'image_choice': chat_ico,},\
                                       current_users=current_users, current_user=request.user.account) if anon_prov else \
                   ReNewChatFormBase(initial={'chat_text': text, 'chat_name': name, 'image_choice': chat_ico,}, current_users=current_users, current_user=request.user.account)

        return render(request, 'messenger/chats_edit_n.html', {'form': form,  'chat': chat_,})
    else: return HttpResponse("<h2>Я, конечно, всё понимаю, но <em>этого</em> мне не понять...<br/>К сожалению, вы можете редактировать только те чаты, создателем которых вы являетесь.<a href=\"/\">Назад...</a></h2>")

@permission_required('lfmsh.staff_')
@permission_required('lfmsh.register')
def update_all_pass(request):
    return render(request, 'messenger/update_all_pass.html')

def new_announcement_add(request):
    def prov(img: str) -> bool:
        flag = True
        with os.scandir(os.path.join(settings.STATIC_ROOT, 'uploads')) as listOfEntries:
            for entry in listOfEntries:
                # печать всех записей, являющихся файлами
                if entry.is_file():
                    print(entry.name, img)
                    if img == entry.name:
                        flag = False
                        break
        return flag

    flag = request.user.has_perm('lfmsh.ant_edit')
    if request.method == 'POST':
        form = NewAnnouncementFullForm(request.POST, request.FILES) if flag else NewAnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            plan_ = announcement()
            plan_.id = uuid.uuid4()
            plan_.name = form.cleaned_data['name']
            plan_.text = form.cleaned_data['text']
            image = form.cleaned_data['picture']
            if image:
                name = str(image.name)
                try:
                    i = 0
                    end = f".{name.split('.')[-1]}"
                    name_x = name
                    while not prov(name_x):
                        name_x = f"{'.'.join(name.split('.')[:-1])}{i}{end}"
                        i += 1
                    name = name_x
                    plan_.picture = name
                    with open(os.path.join(settings.STATIC_ROOT, 'uploads', name), 'wb') as file:
                        for chunk in image.chunks():
                            file.write(chunk)
                except FileNotFoundError:
                    os.makedirs(os.path.join(settings.STATIC_ROOT, 'uploads'))
                    with open(os.path.join(settings.STATIC_ROOT, 'uploads', image.name), 'wb') as file:
                        for chunk in image.chunks():
                            file.write(chunk)
            plan_.orientation = form.cleaned_data['type_']
            if announcement.objects.all().exists(): number = list(announcement.objects.all().order_by('-number'))[-1].number + 1
            else: number = 1
            plan_.number = number
            if flag: plan_.creator = form.cleaned_data['creator']
            else: plan_.creator = request.user.account
            plan_.save()
            return redirect('index')
    else:
        text = name = ''
        initial={'text': text, 'name': name,}
        form = NewAnnouncementFullForm(initial=initial) if flag else NewAnnouncementForm(initial=initial)
    return render(request, 'messenger/ant_new.html', {'form': form,})

@permission_required('lfmsh.staff_')
@permission_required('lfmsh.ant_edit')
def re_new_announcement_add(request, pk):
    plan_ = get_object_or_404(announcement, id=pk)
    if request.method == 'POST':
        form = ReNewAnnouncementForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['delete']:
                plan_.delete()
            else:
                plan_.creator = form.cleaned_data['creator']
                plan_.status = form.cleaned_data['status']
                plan_.save()
            return redirect('plans-new')
    else:
        creator = plan_.creator
        form = ReNewAnnouncementForm(initial={'creator': creator,})
    return render(request, 'messenger/form_edit_for_all.html', {'form': form, 'delta': 'объявления'})
