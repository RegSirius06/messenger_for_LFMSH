from django.urls import re_path
from lfmsh import views
#from django.conf.urls import url

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^announcement/new/$', views.new_announcement_add, name='plans'),
    re_path(r'^announcement/edit/$', views.plan_x, name='plans-new'),
    re_path(r'^announcement/edit/(?P<pk>[-\w]+)/$', views.re_new_announcement_add, name='plans-new-n'),

    re_path(r'^messages/$', views.home, name='messages'),
    re_path(r'^messages/new/$', views.new_message_add, name='messages-new'),
    re_path(r'^messages/edit/$', views.home_send, name='messages-edit'),
    re_path(r'^messages/edit/(?P<pk>[-\w]+)/$', views.re_new_message_add, name='messages-edit-n'),

    re_path(r'^chats/new/$', views.new_chat_add, name='chats-new'),
    re_path(r'^chats/new/conflict/(?P<new_chat_id>[-\w]+)/(?P<new_message_id>[-\w]+)/(?P<new_chat_valid_id>[-\w]+)/(?P<existing_chat_id>[-\w]+)/$',
            views.new_chat_add_confilct, name='chats-new-conflict'),
    re_path(r'^chats/archive/$', views.chat_archive, name='chats-archived'),
    re_path(r'^chats/archive/(?P<pk>[-\w]+)/$', views.chat_archived_view, name='chats-archived-n'),
    re_path(r'update_messages/(?P<pk>[-\w]+)/', views.update_msgs, name='update-messages'),
    re_path(r'^chats/(?P<pk>[-\w]+)/$', views.chat_view, name='chats-n'),
    re_path(r'^chats/(?P<pk>[-\w]+)/edit/$', views.re_new_chat_add, name='chats-edit-n'),
    
    re_path(r'^account/info/$', views.account_info, name='info-users'),
    re_path(r'^account/create/$', views.new_account_add, name='new-user'),
    re_path(r'^account/create/custom/$', views.new_account_full_add, name='new-user-custom'),
    re_path(r'^account/edit/all_pass/$', views.update_all_pass, name='update-all-pass'),
    re_path(r'^account/edit/(?P<pk>[-\w]+)/$', views.re_new_account_full_add, name='account-edit-n'),
]